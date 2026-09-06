from pathlib import Path
import tempfile

def transcribe_audio(audio_file):
    """Transcribe Streamlit audio_input bytes using Google Speech Recognition. No API key is required.
    Returns (text, error). Internet access is required for the recognition service.
    """
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_file.getvalue())
            path = f.name
        with sr.AudioFile(path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        return text, None
    except Exception as exc:
        return "", str(exc)

def speak_to_file(text):
    """Create a local WAV for browser playback when pyttsx3 is available."""
    try:
        import pyttsx3
        path = Path(tempfile.gettempdir()) / "ai_industrial_guardian_voice.wav"
        engine = pyttsx3.init()
        engine.save_to_file(text, str(path))
        engine.runAndWait()
        return path if path.exists() else None
    except Exception:
        return None
