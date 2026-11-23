"""The UI previews the exact plan. This module executes approved local steps."""

from knowledge_store import forget, open_store, remember, search


def parse_plan(text):
    steps = []
    for line in text.splitlines():
        if not line.strip():
            continue
        name, _, argument = line.strip().partition(" ")
        name = name.casefold()
        argument = argument.strip()
        if name not in ("remember", "forget", "search") or not argument:
            raise ValueError("Each line must be: remember TEXT, forget ID, or search WORDS.")
        if name == "forget" and not (
            argument.isascii() and argument.isdecimal() and len(argument) < 19
        ):
            raise ValueError("Use a numeric memory ID after forget.")
        steps.append((name, argument))
    if not 1 <= len(steps) <= 12:
        raise ValueError("Use between one and twelve steps.")
    return tuple(steps)


def run_plan(folder, text, confirm, database=None):
    steps = parse_plan(text)
    preview = "\n".join(f"{i}. {name} {arg}" for i, (name, arg) in enumerate(steps, 1))
    if confirm(preview) is not True:
        return "Cancelled."
    results = []
    with open_store(database) as db:
        for name, arg in steps:
            if name == "remember":
                memory_id = remember(db, folder, arg)
                results.append(f"Saved memory #{memory_id}.")
            elif name == "forget":
                forget(db, folder, int(arg))
                results.append(f"Removed memory #{arg}.")
            else:
                matches = search(db, folder, arg)
                results.extend(f"[{row['source']}] {row['content']}" for row in matches)
                if not matches:
                    results.append("No matches in this folder.")
    return "\n".join(results)
