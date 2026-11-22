"""Pre-Breaker boundaries and an integrated worker-to-provider request."""

import copy
import tempfile
import unittest
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, Mock, patch

import action_tools
import context_engine
import conversation_data
import knowledge_store as store
import model_providers as providers
import settings_data as settings
import voice_io
from request_worker import run_ai_worker


class PreBreakerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.database = self.root / "knowledge.db"
        self.settings_file = self.root / "settings.json"

    def test_legacy_preferences_cloud_consent_and_atomic_replacement(self):
        old = copy.deepcopy(settings.DEFAULT_SETTINGS)
        del old["selected_models"]["openai"]
        settings.save_settings(old, self.settings_file)
        loaded = settings.load_settings(self.settings_file)
        self.assertIn("openai", loaded["selected_models"])
        with self.assertRaises(ValueError):
            settings.update_model_preference(loaded, "gemini", "example")
        updated = settings.update_model_preference(loaded, "gemini", "example", allow_cloud=True)
        with patch("pathlib.Path.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                settings.save_settings(updated, self.settings_file)
        self.assertEqual(settings.load_settings(self.settings_file), loaded)
        self.assertEqual(list(self.root.iterdir()), [self.settings_file])
        for value in (None, [], "qwen"):
            self.assertFalse(settings.validate_settings({**old, "selected_models": value}))
        self.settings_file.write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            settings.load_settings(self.settings_file)

    def test_worker_routes_to_each_chosen_cloud_model_only(self):
        messages = [{"role": "user", "content": "Hello"}]
        for name, (variable, url) in providers.CLOUD_ENDPOINTS.items():
            with (
                self.subTest(provider=name),
                patch.dict("os.environ", {variable: "test"}, clear=True),
                patch("model_providers.OpenAI") as client,
                patch("model_providers.requests.post") as local,
            ):
                complete = client.return_value.__enter__.return_value.chat.completions.create
                complete.return_value.choices = [Mock(message=Mock(content=" OK "))]
                results = Queue()
                run_ai_worker("id", "folder", "chat", name, messages, results, model="chosen")
                self.assertEqual(results.get_nowait()["response"], "OK")
                self.assertEqual(client.call_args.kwargs["base_url"], url)
                complete.assert_called_once_with(model="chosen", messages=messages)
                local.assert_not_called()

    def test_missing_cloud_key_never_falls_back(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("model_providers.requests.post") as local,
        ):
            with self.assertRaisesRegex(providers.ModelProviderError, "GROQ_API_KEY"):
                providers.generate_messages([{"role": "user", "content": "Hi"}], "groq", "model")
            local.assert_not_called()

    def test_ollama_discovery_and_pinned_model(self):
        with patch("model_providers.requests.get") as get:
            get.return_value.json.return_value = {"models": [{"name": "local-v2"}, {}]}
            self.assertEqual(providers.list_ollama_models(), ["local-v2"])
        with patch("model_providers.requests.post") as post:
            post.return_value.json.return_value = {"message": {"content": "hi"}}
            providers.generate_messages([{"role": "user", "content": "Hi"}], model="local-v2")
            self.assertEqual(post.call_args.kwargs["json"]["model"], "local-v2")

    def test_searchable_import_replaces_old_text_and_isolated_from_other_folders(self):
        path = self.root / "notes.md"
        path.write_text("Our preferred database is sqlite.", encoding="utf-8")
        store.import_document("a", path, self.database)
        with patch.object(store, "DATABASE", self.database):
            self.assertIn("notes.md", store.references("a", "database")[0])
            self.assertNotIn(str(self.root), store.references("a", "database")[0])
            self.assertFalse(store.references("b", "database"))
            path.write_text("We switched to postgres.", encoding="utf-8")
            store.import_document("a", path, self.database)
            self.assertFalse(store.references("a", "sqlite"))
            self.assertTrue(store.references("a", "postgres"))

    def test_denied_or_failed_plan_changes_nothing(self):
        cancel = action_tools.run_plan("a", "remember secrets", lambda _: False, self.database)
        self.assertEqual(cancel, "Cancelled.")
        self.assertFalse(self.database.exists())
        with self.assertRaises(ValueError):
            action_tools.run_plan("a", "remember one\nforget 999", lambda _: True, self.database)
        with store.open_store(self.database) as db:
            self.assertFalse(store.list_memories(db, "a"))
        result = action_tools.run_plan(
            "a", "remember recipe\nsearch recipe", lambda _: True, self.database
        )
        self.assertIn("recipe", result)
        with store.open_store(self.database) as db:
            memory_id = store.list_memories(db, "a")[0]["id"]
            with self.assertRaises(ValueError):
                store.forget(db, "b", memory_id)
            store.forget(db, "a", memory_id)
            self.assertFalse(store.search(db, "a", "recipe"))

    def test_context_keeps_latest_turn_and_an_extract_from_older_turns(self):
        chat = [
            {"role": "user", "content": "Use sqlite. Another sentence."},
            {"role": "optimizer", "content": "x" * 16000},
            {"role": "user", "content": "Why sqlite?"},
        ]
        older, recent = context_engine.split_history(chat, 4)
        self.assertEqual(recent, chat[-1:])
        self.assertIn("user: Use sqlite", context_engine.summarize_history(older))

    def test_offline_speech_driver_reads_text_and_stops(self):
        engine = Mock()
        with patch.dict("sys.modules", {"pyttsx3": Mock(init=Mock(return_value=engine))}):
            voice_io.speak("Hello")
        engine.say.assert_called_once_with("Hello")
        engine.runAndWait.assert_called_once()
        engine.stop.assert_called_once()

    def test_dictation_releases_mic_before_recognition(self):
        fake = Mock()
        mic = MagicMock()
        fake.Microphone.return_value = mic
        recognizer = fake.Recognizer.return_value

        def decode(audio):
            mic.__exit__.assert_called_once()
            return "  hello  "

        recognizer.recognize_sphinx.side_effect = decode
        with patch.dict("sys.modules", {"speech_recognition": fake}):
            self.assertEqual(voice_io.dictate(), "hello")
        recognizer.listen.assert_called_once_with(
            mic.__enter__.return_value, timeout=5, phrase_time_limit=12
        )

    def test_folder_references_and_recent_chat_flow_into_snapshot_together(self):
        folders = {"folders": []}
        with (
            patch.object(conversation_data, "OPTIMIZER_DATA", folders),
            patch.object(store, "DATABASE", self.database),
        ):
            for name in ("physics", "music"):
                conversation_data.create_folder(name, name)
                conversation_data.create_conversation(name, name, "Questions")
                conversation_data.add_message(name, name, "user", "Which telescope filter?")
            action_tools.run_plan("physics", "Remember telescope filter is cobalt", lambda _: True)
            path = self.root / "spec.md"
            path.write_text("The telescope is 1000 mm.", encoding="utf-8")
            store.import_document("physics", path)
            physics = context_engine.build_model_messages("physics", "physics")
            music = context_engine.build_model_messages("music", "music")
            texts = [message["content"] for message in physics[:-1]]
            self.assertTrue(any("cobalt" in text and "spec.md" in text for text in texts))
            self.assertFalse(
                any("cobalt" in msg["content"] or "spec.md" in msg["content"] for msg in music)
            )
            self.assertEqual(physics[-1], {"role": "user", "content": "Which telescope filter?"})

    def test_settings_require_explicit_cloud_consent_and_text_model(self):
        for permission in (None, 1, "yes", False):
            with self.subTest(permission=permission), self.assertRaises(ValueError):
                settings.update_model_preference(
                    settings.DEFAULT_SETTINGS, "groq", "model", allow_cloud=permission
                )
        with self.assertRaises(ValueError):
            settings.update_model_preference(settings.DEFAULT_SETTINGS, "ollama", 4)
