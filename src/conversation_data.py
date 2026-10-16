import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "conversations.json"

OPTIMIZER_DATA = {
    "folders": []
    }
general_folder = {
    "id": "folder_general",
    "name": "General",
    "instructions": "",
    "knowledge": [],
    "conversations": []
    }

ACTIVE_SELECTION = {
    "folder_id": "folder_general",
    "conversation_id": None
}

OPTIMIZER_DATA["folders"].append(general_folder)

def create_folder(folder_id, folder_name):
    if not isinstance(folder_name, str):
        return False

    if not isinstance(folder_id, str):
        return False

    folder_id = folder_id.strip()
    folder_name = folder_name.strip()

    if not folder_name:
        return False

    if not folder_id:
        return False

    for folder in OPTIMIZER_DATA["folders"]:
        if folder["id"] == folder_id:
            return False

    new_folder = {
        "id": folder_id,
        "name": folder_name,
        "instructions": "",
        "knowledge": [],
        "conversations": []
    }

    OPTIMIZER_DATA["folders"].append(new_folder)
    return True

def get_all_folders():
    copy = OPTIMIZER_DATA["folders"].copy()
    return copy

def get_folder(folder_id):
    list_data = OPTIMIZER_DATA["folders"]

    for folder in list_data:
        if folder["id"] == folder_id:
            return folder

    return None

def create_conversation(folder_id, conversation_id, title):
    if not isinstance(folder_id, str):
        return False

    if not isinstance(conversation_id, str):
        return False

    if not isinstance(title, str):
        return False

    folder_id = folder_id.strip()
    conversation_id = conversation_id.strip()
    title = title.strip()

    if not folder_id or not conversation_id or not title:
        return False

    target_folder = get_folder(folder_id)

    if target_folder is None:
        return False

    for folder in OPTIMIZER_DATA["folders"]:

        for existing_conversation in folder["conversations"]:

            if existing_conversation["id"] == conversation_id:
                return False

    new_conversation = {
        "id": conversation_id,
        "title": title,
        "messages": []
    }

    target_folder['conversations'].append(new_conversation)
    return True

def get_all_conversations(folder_id):
    target_folder = get_folder(folder_id)

    if target_folder is None:
        return None

    conversations = target_folder["conversations"].copy()

    return conversations

def get_conversation(folder_id, conversation_id):
    target_folder = get_folder(folder_id)

    if target_folder is None:
        return None

    for conversation in target_folder["conversations"]:
        if conversation["id"] == conversation_id:

            return conversation

    return None

def select_conversation(folder_id, conversation_id):
    selected_conversation = get_conversation(folder_id,  conversation_id)

    if selected_conversation is None:
        return False

    ACTIVE_SELECTION["folder_id"] = folder_id
    ACTIVE_SELECTION["conversation_id"] = conversation_id

    return True

def get_selected_conversation():
    active_folder_id = ACTIVE_SELECTION["folder_id"]
    active_conversation_id = ACTIVE_SELECTION["conversation_id"]

    if active_conversation_id is None:
        return None

    conversation = get_conversation(active_folder_id, active_conversation_id)

    return conversation

def add_message(folder_id, conversation_id, role, content):
    if not isinstance(folder_id, str):
        return False

    if not isinstance(conversation_id, str):
        return False

    if not isinstance(role, str):
        return False

    if not isinstance(content, str):
        return False

    folder_id = folder_id.strip()
    conversation_id = conversation_id.strip()
    role = role.strip()

    if not folder_id or not conversation_id:
        return False

    if not content.strip():
        return False

    if role not in ("user", "optimizer"):
        return False

    target_conversation = get_conversation(folder_id, conversation_id)

    if target_conversation is None:
        return False

    new_message = {
        "role": role,
        "content": content
    }

    target_conversation["messages"].append(new_message)

    return True

def get_messages(folder_id, conversation_id):
    target_conversation = get_conversation(folder_id, conversation_id)

    if target_conversation is None:
        return None

    message_copies = []

    for message in target_conversation["messages"]:
        message_copies.append(message.copy())

    return message_copies

def get_selected_messages():
    active_folder_id = ACTIVE_SELECTION["folder_id"]
    active_conversation_id = ACTIVE_SELECTION["conversation_id"]

    if active_conversation_id is None:
        return None

    messages = get_messages(active_folder_id, active_conversation_id)

    return messages

def save_data(file_path = None):
    if file_path is None:
        destination = DATA_FILE
    
    else:
        destination = Path(file_path)

    temporary = destination.with_name(destination.name + ".tmp")

    try:
        destination.parent.mkdir(parents = True, exist_ok = True)

        with temporary.open("w", encoding = "utf-8")as file:
            json.dump(OPTIMIZER_DATA,
                      file,
                      indent = 4,
                      ensure_ascii = False
                      )

        temporary.replace(destination)
        return True

    except (OSError, TypeError):
        try:
            temporary.unlink(missing_ok = True)
        except OSError:
            pass

        return False

def validate_loaded_data(loaded_data):
    if not isinstance(loaded_data, dict):
        return False

    folders = loaded_data.get("folders")

    if not isinstance(folders, list):
        return False

    seen_folder_ids = set()
    seen_conversation_ids = set()

    for folder in folders:
        if not isinstance(folder, dict):
            return False

        required_folder_keys = (
            "id",
            "name",
            "instructions",
            "knowledge",
            "conversations"
        )

        for key in required_folder_keys:
            if key not in folder:
                return False

        if not isinstance(folder["id"], str):
            return False

        if not folder["id"].strip():
            return False

        if not isinstance(folder["name"], str):
            return False

        if not folder["name"].strip():
            return False

        if not isinstance(folder["instructions"], str):
            return False

        if not isinstance(folder["knowledge"], list):
            return False

        if not isinstance(folder["conversations"], list):
            return False

        for knowledge_item in folder["knowledge"]:
            if not isinstance(knowledge_item, str):
                return False

        if folder["id"] in seen_folder_ids:
            return False

        seen_folder_ids.add(folder["id"])

        for conversation in folder["conversations"]:
            if not isinstance(conversation, dict):
                return False

            required_keys = (
                "id",
                "title",
                "messages"
            )

            for conversation_key in required_keys:
                if conversation_key not in conversation:
                    return False

            if not isinstance(conversation["id"], str):
                return False

            if not conversation["id"].strip():
                return False

            if not isinstance(conversation["title"], str):
                return False

            if not conversation["title"].strip():
                return False

            if not isinstance(conversation["messages"], list):
                return False

            if conversation["id"] in seen_conversation_ids:
                return False

            seen_conversation_ids.add(conversation['id'])

            for message in conversation["messages"]:
                if not isinstance(message, dict):
                    return False

                verify_keys = (
                    "role",
                    "content"
                )

                for key in verify_keys:
                    if key not in message:
                        return False

                if not isinstance(message["role"], str):
                    return False

                if message["role"] not in ("user", "optimizer"):
                    return False

                if not isinstance(message["content"], str):
                    return False

                if not message["content"].strip():
                    return False

    if "folder_general" not in seen_folder_ids:
        return False

    return True


def load_data(file_path = None):
    if file_path is None:
        source = DATA_FILE
    else:
        source = Path(file_path)

    try:
        if not source.exists():
            return "missing"

        with source.open("r", encoding = "utf-8") as file:
            loaded_data = json.load(file)

    except (json.JSONDecodeError, UnicodeDecodeError):
        return "invalid"

    except OSError:
        return "error"

    if not validate_loaded_data(loaded_data):
        return "invalid"

    OPTIMIZER_DATA.clear()
    OPTIMIZER_DATA.update(loaded_data)

    ACTIVE_SELECTION["folder_id"] = "folder_general"
    ACTIVE_SELECTION["conversation_id"] = None

    return "loaded"

def get_folder_context(folder_id):
    if not isinstance(folder_id, str):
        return None

    folder_id = folder_id.strip()

    if not folder_id:
        return None

    target_folder = get_folder(folder_id)

    if target_folder is None:
        return None

    folder_context = {
        "id": target_folder["id"],
        "name": target_folder["name"],
        "instructions": target_folder["instructions"],
        "knowledge": target_folder["knowledge"].copy()
    }

    return folder_context

def update_folder_instructions(folder_id, instructions):
    if not isinstance(folder_id, str):
        return False

    if not isinstance(instructions, str):
        return False

    folder_id = folder_id.strip()

    if not folder_id:
        return False

    target_folder = get_folder(folder_id)

    if target_folder is None:
        return False

    clean_instructions = instructions.strip()

    target_folder["instructions"] = clean_instructions

    return True

def add_folder_knowledge(folder_id, note):
    if not isinstance(folder_id, str):
        return False

    if not isinstance(note, str):
        return False

    folder_id = folder_id.strip()
    note = note.strip()

    if not folder_id:
        return False

    if not note:
        return False

    target_folder = get_folder(folder_id)

    if target_folder is None:
        return False

    if note in target_folder["knowledge"]:
        return False

    target_folder["knowledge"].append(note)

    return True

def remove_folder_knowledge(folder_id, index):
    if not isinstance(folder_id, str):
        return False

    folder_id = folder_id.strip()

    if not folder_id:
        return False

    if not isinstance(index, int):
        return False

    if isinstance(index, bool):
        return False

    target_folder = get_folder(folder_id)

    if target_folder is None:
        return False

    knowledge = target_folder["knowledge"]

    if index < 0:
        return False

    if index >= len(knowledge):
        return False

    knowledge.pop(index)

    return True

