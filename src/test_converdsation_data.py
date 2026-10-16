
import conversation_data as data
import json

from pathlib import Path
from tempfile import TemporaryDirectory


def test_conversation_system():

    print("\n=== FOLDER MANAGEMENT ===")

    # Test 1
    assert data.create_folder(
        "folder_dizone", "DI-ZONE Development"
    ) is True

    assert data.create_folder(
        "folder_school", "School"
    ) is True
    print("PASS 1: Folder creation")

    # Test 2
    assert data.create_folder(
        "folder_dizone", "Duplicate"
    ) is False
    print("PASS 2: Duplicate folder rejection")

    # Test 3
    folder = data.get_folder("folder_dizone")
    assert folder is not None
    assert folder["name"] == "DI-ZONE Development"
    print("PASS 3: Folder retrieval")

    # Test 4
    assert len(data.get_all_folders()) == 3
    print("PASS 4: Retrieve all folders")

    # Test 5
    assert data.get_folder("folder_missing") is None
    print("PASS 5: Missing folder handling")


    print("\n=== CONVERSATION MANAGEMENT ===")

    # Test 6
    assert data.create_conversation(
        "folder_dizone", "chat_001", "Optimizer Development"
    ) is True

    assert data.create_conversation(
        "folder_dizone", "chat_002", "Student Code Review"
    ) is True
    print("PASS 6: Conversation creation")

    # Test 7
    assert data.create_conversation(
        "folder_school", "chat_001", "Duplicate"
    ) is False
    print("PASS 7: Duplicate conversation ID")

    # Test 8
    assert data.create_conversation(
        "folder_dizone", "", "Invalid"
    ) is False

    assert data.create_conversation(
        "folder_dizone", "chat_003", ""
    ) is False
    print("PASS 8: Invalid conversation data")

    # Test 9
    assert data.create_conversation(
        "folder_missing", "chat_004", "Invalid"
    ) is False
    print("PASS 9: Invalid destination folder")

    # Test 10
    conversations = data.get_all_conversations("folder_dizone")
    assert len(conversations) == 2
    assert conversations[0]["title"] == "Optimizer Development"
    assert conversations[1]["title"] == "Student Code Review"
    print("PASS 10: Folder conversations")

    # Test 11
    assert data.get_all_conversations("folder_school") == []
    print("PASS 11: Folder isolation")

    # Test 12
    conversation = data.get_conversation(
        "folder_dizone", "chat_002"
    )
    assert conversation is not None
    assert conversation["title"] == "Student Code Review"
    assert conversation["messages"] == []
    print("PASS 12: Specific conversation retrieval")

    # Test 13
    assert data.get_conversation(
        "folder_dizone", "chat_missing"
    ) is None
    print("PASS 13: Missing conversation handling")


    print("\n=== ACTIVE CONVERSATION SELECTION ===")

    # Test 14
    assert data.get_selected_conversation() is None
    print("PASS 14: Initial selection")

    # Test 15
    assert data.select_conversation(
        "folder_dizone", "chat_001"
    ) is True
    print("PASS 15: Select conversation")

    # Test 16
    assert data.ACTIVE_SELECTION["folder_id"] == "folder_dizone"
    assert data.ACTIVE_SELECTION["conversation_id"] == "chat_001"
    print("PASS 16: Selection state")

    # Test 17
    selected = data.get_selected_conversation()
    assert selected["title"] == "Optimizer Development"
    print("PASS 17: Selected conversation retrieval")

    # Test 18
    assert data.select_conversation(
        "folder_dizone", "chat_missing"
    ) is False

    assert data.get_selected_conversation()["id"] == "chat_001"
    print("PASS 18: Invalid selection protection")

    # Test 19
    assert data.create_conversation(
        "folder_school", "chat_school_001", "College Algebra"
    ) is True

    assert data.select_conversation(
        "folder_school", "chat_school_001"
    ) is True

    assert data.get_selected_conversation()["title"] == "College Algebra"
    print("PASS 19: Cross-folder selection")


    print("\n=== MESSAGE MANAGEMENT ===")

    # Test 20
    assert data.get_messages("folder_dizone", "chat_001") == []
    print("PASS 20: Empty history")

    # Test 21
    assert data.add_message(
        "folder_dizone", "chat_001",
        "user", "Hello Optimizer!"
    ) is True
    print("PASS 21: User message")

    # Test 22
    assert data.add_message(
        "folder_dizone", "chat_001",
        "optimizer", "[Prototype] Hello!"
    ) is True
    print("PASS 22: Optimizer message")

    # Test 23
    messages = data.get_messages("folder_dizone", "chat_001")
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "optimizer"
    assert messages[0]["content"] == "Hello Optimizer!"
    print("PASS 23: Message ordering")

    # Test 24
    assert data.get_messages("folder_dizone", "chat_002") == []
    assert data.get_messages("folder_school", "chat_school_001") == []
    print("PASS 24: Independent histories")

    # Test 25
    assert data.add_message(
        "folder_dizone", "chat_001", "user", "   "
    ) is False

    assert data.add_message(
        "folder_dizone", "chat_001", "system", "Invalid"
    ) is False

    assert data.add_message(
        "folder_dizone", "chat_001", "user", 123
    ) is False
    print("PASS 25: Invalid message rejection")

    # Test 26
    assert data.add_message(
        "folder_dizone", "chat_missing",
        "user", "Test"
    ) is False

    assert data.get_messages(
        "folder_dizone", "chat_missing"
    ) is None
    print("PASS 26: Missing destination")

    # Test 27
    outside = data.get_messages("folder_dizone", "chat_001")
    outside[0]["content"] = "Changed"
    outside.append({"role": "user", "content": "Fake"})

    stored = data.get_messages("folder_dizone", "chat_001")
    assert len(stored) == 2
    assert stored[0]["content"] == "Hello Optimizer!"
    print("PASS 27: Message copies")

    # Test 28
    assert data.get_selected_messages() == []

    assert data.add_message(
        "folder_school", "chat_school_001",
        "user", "Explain algebra"
    ) is True

    selected_messages = data.get_selected_messages()
    assert len(selected_messages) == 1
    assert selected_messages[0]["content"] == "Explain algebra"
    print("PASS 28: Selected chat history")


    print("\n=== JSON PERSISTENCE ===")

    # Prepare existing shared context
    assert data.update_folder_instructions(
        "folder_dizone",
        "Explain programming using clear pseudocode."
    ) is True

    assert data.add_folder_knowledge(
        "folder_dizone",
        "DI-ZONE Optimizer is a Python application."
    ) is True

    with TemporaryDirectory() as temp_dir:

        test_path = Path(temp_dir) / "conversations.json"

        # Test 29
        assert data.save_data(test_path) is True
        assert test_path.exists()
        print("PASS 29: Save data")

        # Test 30
        saved_data = json.loads(
            test_path.read_text(encoding="utf-8")
        )

        assert "folders" in saved_data
        assert len(saved_data["folders"]) == 3

        saved_folder = next(
            folder for folder in saved_data["folders"]
            if folder["id"] == "folder_dizone"
        )

        assert saved_folder["instructions"] == (
            "Explain programming using clear pseudocode."
        )
        assert len(saved_folder["knowledge"]) == 1
        print("PASS 30: Saved JSON and context")

        # Test 31
        data.OPTIMIZER_DATA["folders"].clear()

        assert data.load_data(test_path) == "loaded"

        restored = data.get_folder("folder_dizone")
        assert restored is not None

        assert restored["instructions"] == (
            "Explain programming using clear pseudocode."
        )

        assert restored["knowledge"] == [
            "DI-ZONE Optimizer is a Python application."
        ]

        assert len(
            data.get_messages("folder_dizone", "chat_001")
        ) == 2

        assert len(
            data.get_messages("folder_school", "chat_school_001")
        ) == 1

        print("PASS 31: Restore saved data")

        # Test 32
        assert data.get_selected_conversation() is None
        assert data.ACTIVE_SELECTION["folder_id"] == "folder_general"
        assert data.ACTIVE_SELECTION["conversation_id"] is None
        print("PASS 32: Selection reset")

        # Test 33
        missing_path = Path(temp_dir) / "missing.json"

        assert data.load_data(missing_path) == "missing"
        assert data.get_folder("folder_dizone") is not None
        print("PASS 33: Missing file handling")

        # Test 34
        damaged_path = Path(temp_dir) / "damaged.json"
        damaged_path.write_text(
            "{invalid json", encoding="utf-8"
        )

        assert data.load_data(damaged_path) == "invalid"
        assert data.get_folder("folder_dizone") is not None
        print("PASS 34: Malformed JSON")

        # Test 35
        invalid_path = Path(temp_dir) / "invalid.json"
        invalid_path.write_text(
            '{"folders": [{"id": "broken"}]}',
            encoding="utf-8"
        )

        assert data.load_data(invalid_path) == "invalid"
        assert data.get_folder("folder_dizone") is not None
        print("PASS 35: Invalid structure protection")


    print("\n=== FOLDER CONTEXT MANAGEMENT ===")

    # Test 36: Retrieve independent folder context
    context = data.get_folder_context("folder_school")

    assert context is not None
    assert context["id"] == "folder_school"
    assert context["name"] == "School"
    assert context["instructions"] == ""
    assert context["knowledge"] == []

    context["knowledge"].append("External change")

    assert data.get_folder_context("folder_school")["knowledge"] == []
    assert data.get_folder_context("folder_missing") is None

    print("PASS 36: Folder context retrieval and copying")

    # Test 37: Update instructions
    assert data.update_folder_instructions(
        "folder_school",
        "  Explain topics using examples.  "
    ) is True

    assert data.get_folder_context("folder_school")["instructions"] == (
        "Explain topics using examples."
    )

    print("PASS 37: Update shared instructions")

    # Test 38: Clear instructions
    assert data.update_folder_instructions(
        "folder_school", "   "
    ) is True

    assert data.get_folder_context("folder_school")["instructions"] == ""

    print("PASS 38: Clear folder instructions")

    # Test 39: Reject invalid instructions
    assert data.update_folder_instructions(
        "folder_school", None
    ) is False

    assert data.update_folder_instructions(
        "folder_missing", "Invalid destination"
    ) is False

    assert data.update_folder_instructions(
        "", "Invalid folder ID"
    ) is False

    assert data.get_folder_context("folder_school")["instructions"] == ""

    print("PASS 39: Invalid instruction updates")

    # Test 40: Add knowledge notes
    assert data.add_folder_knowledge(
        "folder_school", "  College Algebra uses functions.  "
    ) is True

    assert data.add_folder_knowledge(
        "folder_school", "Quadratic equations are studied in algebra."
    ) is True

    context = data.get_folder_context("folder_school")

    assert context["knowledge"] == [
        "College Algebra uses functions.",
        "Quadratic equations are studied in algebra."
    ]

    print("PASS 40: Add shared knowledge")

    # Test 41: Reject invalid or duplicate notes
    assert data.add_folder_knowledge(
        "folder_school", "   "
    ) is False

    assert data.add_folder_knowledge(
        "folder_school", 123
    ) is False

    assert data.add_folder_knowledge(
        "folder_missing", "Invalid destination"
    ) is False

    assert data.add_folder_knowledge(
        "folder_school", "College Algebra uses functions."
    ) is False

    assert len(
        data.get_folder_context("folder_school")["knowledge"]
    ) == 2

    print("PASS 41: Invalid and duplicate knowledge")

    # Test 42: Remove and validate knowledge indexes
    assert data.remove_folder_knowledge(
        "folder_school", 0
    ) is True

    assert data.get_folder_context("folder_school")["knowledge"] == [
        "Quadratic equations are studied in algebra."
    ]

    assert data.remove_folder_knowledge(
        "folder_school", -1
    ) is False

    assert data.remove_folder_knowledge(
        "folder_school", 10
    ) is False

    assert data.remove_folder_knowledge(
        "folder_school", True
    ) is False

    assert data.remove_folder_knowledge(
        "folder_missing", 0
    ) is False

    assert len(
        data.get_folder_context("folder_school")["knowledge"]
    ) == 1

    print("PASS 42: Remove knowledge safely")

    # Test 43: Save and restore updated context
    assert data.update_folder_instructions(
        "folder_school",
        "Explain algebra step by step."
    ) is True

    with TemporaryDirectory() as temp_dir:
        context_path = Path(temp_dir) / "context_test.json"

        assert data.save_data(context_path) is True

        data.OPTIMIZER_DATA["folders"].clear()

        assert data.load_data(context_path) == "loaded"

        restored_context = data.get_folder_context(
            "folder_school"
        )

        assert restored_context is not None

        assert restored_context["instructions"] == (
            "Explain algebra step by step."
        )

        assert restored_context["knowledge"] == [
            "Quadratic equations are studied in algebra."
        ]

        assert len(
            data.get_messages("folder_school", "chat_school_001")
        ) == 1

    print("PASS 43: Shared context persistence")


    print("\n========================================")
    print("ALL 43 TESTS PASSED")
    print("DI-ZONE Optimizer Data Layer: VERIFIED")
    print("========================================")


if __name__ == "__main__":
    test_conversation_system()
