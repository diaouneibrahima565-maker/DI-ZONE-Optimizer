"""One local speech operation per process so Stop can release the audio device."""

import sys


def transcribe(audio, recognizer):
    import speech_recognition as sr

    try:
        return recognizer.recognize_sphinx(audio).strip()
    except sr.UnknownValueError as error:
        raise ValueError("No clear speech was recognized. Try again.") from error


def dictate():
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    with sr.Microphone() as mic:
        try:
            audio = recognizer.listen(mic, timeout=5, phrase_time_limit=12)
        except sr.WaitTimeoutError as error:
            raise ValueError("No speech detected within five seconds.") from error
    return transcribe(audio, recognizer)


def speak(text):
    import pyttsx3

    engine = pyttsx3.init()
    try:
        engine.say(text)
        engine.runAndWait()
    finally:
        engine.stop()


if __name__ == "__main__":
    try:
        operation = sys.argv[1]
        if operation == "listen":
            print(dictate())
        elif operation == "speak":
            speak(sys.stdin.read())
        else:
            sys.exit("Choose listen or speak.")
    except (ImportError, AttributeError):
        sys.exit(
            "Install the optional packages in requirements-voice.txt and check your audio device."
        )
    except Exception as error:
        sys.exit(f"Voice unavailable: {error}")
