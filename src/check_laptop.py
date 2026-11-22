"""Set up and exercise Optimizer on the machine that runs this file."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def python(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def ask(question):
    try:
        return input(question + " [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def start_ollama(executable):
    env = {**os.environ, "OLLAMA_HOST": "127.0.0.1:11434"}
    if os.name == "nt":
        print("Starting Ollama on localhost. Leave its server window open.")
        subprocess.Popen([executable, "serve"], creationflags=subprocess.CREATE_NEW_CONSOLE, env=env)
        return "the Ollama server window"

    cache = Path(os.getenv("XDG_CACHE_HOME") or Path.home() / ".cache") / "di-zone-optimizer"
    cache.mkdir(parents=True, exist_ok=True)
    log = cache / "ollama.log"
    print(f"Starting Ollama on localhost. Its log is {log}")
    with log.open("ab") as stream:
        subprocess.Popen([executable, "serve"], start_new_session=True, env=env,
                         stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
    return str(log)


def check_ollama():
    import model_providers as models
    import requests

    executable = shutil.which("ollama")
    if os.name == "nt" and not executable and os.getenv("LOCALAPPDATA"):
        installed = Path(os.environ["LOCALAPPDATA"]) / "Programs/Ollama/ollama.exe"
        if installed.is_file():
            executable = str(installed)

    try:
        names = models.list_ollama_models()
    except models.ModelProviderError as error:
        if not isinstance(error.__cause__, requests.ConnectionError):
            raise
        if not executable:
            if os.name == "nt":
                hint = "Open Ollama on Windows, or install it from https://ollama.com/download/windows."
            else:
                hint = ("Start Ollama in Ubuntu, or use Windows Ollama if WSL can reach it at "
                        "127.0.0.1:11434. Linux installation: https://docs.ollama.com/linux")
            raise RuntimeError(hint) from error
        server_log = start_ollama(executable)
        for _ in range(20):
            time.sleep(1)
            try:
                names = models.list_ollama_models()
                break
            except models.ModelProviderError:
                continue
        else:
            raise RuntimeError(f"Ollama still cannot serve localhost:11434. Check {server_log}.")

    # Use the project's standard local model and a synthetic message.
    model = models.OLLAMA_MODEL
    if model not in names:
        if not executable or not ask(f"The server is running. Download the missing {model} model?"):
            raise RuntimeError(f"Model missing. Run ollama pull {model}, then rerun the check.")
        subprocess.run([executable, "pull", model], check=True,
                       env={**os.environ, "OLLAMA_HOST": "127.0.0.1:11434"})
    print(f"Sending a short test to {model}. The first reply can take a minute.")
    answer = models.generate_messages([{"role": "user", "content": "Reply with the word ready."}],
                                      provider_name="ollama", model=model)
    print("Local model replied:", answer[:120])


def check_voice():
    import pyaudio
    from pocketsphinx import Decoder

    Decoder()  # Load the bundled English recognizer.
    devices = pyaudio.PyAudio()
    try:
        print("Default microphone:", devices.get_default_input_device_info()["name"])
        print("Default speakers:", devices.get_default_output_device_info()["name"])
    finally:
        devices.terminate()


def audio_round_trip():
    import voice_io

    voice_io.speak("Optimizer speaker test.")
    if not ask("Did you hear the speaker test?"):
        raise RuntimeError("Speaker playback was not confirmed.")
    print("Speak a short English sentence now.")
    print("Optimizer heard:", voice_io.dictate())
    if not ask("Does that match what you said?"):
        raise RuntimeError("Dictation did not match the spoken sentence.")


def main():
    results = {}

    def check(label, operation):
        print(f"\n--- {label} ---", flush=True)
        try:
            operation()
        except Exception as error:
            print(error)
            results[label] = "FAIL"
            return False
        results[label] = "PASS"
        return True

    print("Optimizer laptop check using", sys.executable, sys.version.split()[0])
    core = check("App packages", lambda: python("-m", "pip", "install", "customtkinter", "pillow",
                                                 "requests", "openai", "pytest"))
    voice = check("Voice packages", lambda: python("-m", "pip", "install", "-r", "requirements-voice.txt"))
    if core:
        check("Desktop imports", lambda: python("-c", "import tkinter, customtkinter, PIL, sqlite3"))
        check("Project tests", lambda: python("-m", "pytest", "-q", "src"))
        check("Local Ollama reply", check_ollama)
    else:
        results.update(dict.fromkeys(("Desktop imports", "Project tests", "Local Ollama reply"), "SKIP"))

    if voice and check("Recognizer and audio devices", check_voice):
        if ask("Play a test phrase and then turn on the microphone for one sentence?"):
            check("Speaker and dictation", audio_round_trip)
    results.setdefault("Recognizer and audio devices", "SKIP")
    results.setdefault("Speaker and dictation", "SKIP")

    print("\nOptimizer laptop results")
    for label, status in results.items():
        print(f"{status:4}  {label}")
    if os.name != "nt":
        print("To launch Optimizer: bash run-ubuntu.sh")
    else:
        print(r"To launch Optimizer with this environment: .\venv\optimizer313\Scripts\python.exe src\main.py")
    return int("FAIL" in results.values())


if __name__ == "__main__":
    raise SystemExit(main())
