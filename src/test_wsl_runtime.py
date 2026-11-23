import io
import json
import os
import subprocess
import unittest
import wave
from unittest.mock import Mock, patch

import model_providers as models
import voice_io


class WindowsLoopbackTests(unittest.TestCase):
    @patch.dict(os.environ, {"OPTIMIZER_USE_WINDOWS_OLLAMA": "1"})
    @patch("subprocess.run")
    def test_windows_discovery_and_chat(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, b'{"models":[{"name":"local"}]}', b"")
        self.assertEqual(models.list_ollama_models(), ["local"])
        self.assertEqual(run.call_args.args[0][-1], "http://127.0.0.1:11434/api/tags")
        run.return_value.stdout = b'{"message":{"content":"Ready"}}'
        messages = [{"role": "user", "content": "hello from Ubuntu"}]
        self.assertEqual(models.generate_messages(messages, model="local"), "Ready")
        self.assertEqual(json.loads(run.call_args.kwargs["input"])["messages"], messages)
        self.assertNotIn("hello from Ubuntu", run.call_args.args[0])

    @patch.dict(os.environ, {"OPTIMIZER_USE_WINDOWS_OLLAMA": "1"})
    @patch("subprocess.run", return_value=subprocess.CompletedProcess([], 7, b"", b"refused"))
    def test_unreachable_windows_server(self, run):
        with self.assertRaisesRegex(models.ModelProviderError, "refused"):
            models.list_ollama_models()


class WslAudioTests(unittest.TestCase):
    def test_sends_synthesized_audio_to_detected_output(self):
        wav = io.BytesIO()
        samples = b"\x00\x01" * 100
        with wave.open(wav, "wb") as out:
            out.setparams((1, 2, 22050, 0, "NONE", "uncompressed"))
            out.writeframes(samples)
        audio = Mock()
        device = audio.PyAudio.return_value
        device.get_default_output_device_info.return_value = {"index": 6, "name": "pulse"}
        with patch.dict("sys.modules", {"pyaudio": audio}), patch("subprocess.run") as synth:
            synth.return_value.stdout = wav.getvalue()
            voice_io.speak_on_wsl("Hello")
        self.assertEqual(synth.call_args.kwargs["input"], b"Hello")
        self.assertEqual(device.open.call_args.kwargs["output_device_index"], 6)
        device.open.return_value.write.assert_called_once_with(samples)
        device.terminate.assert_called_once()
