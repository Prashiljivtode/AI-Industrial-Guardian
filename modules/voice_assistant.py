import os, tempfile

def transcribe(uploaded_audio):
    try:
        import speech_recognition as sr
        r=sr.Recognizer()
        suffix=".wav"
        with tempfile.NamedTemporaryFile(delete=False,suffix=suffix) as f:
            f.write(uploaded_audio.getvalue()); path=f.name
        try:
            with sr.AudioFile(path) as source: audio=r.record(source)
            return r.recognize_google(audio)
        finally:
            try: os.remove(path)
            except OSError: pass
    except Exception as e:
        return f"VOICE_ERROR: {e}"

def speak(text):
    try:
        import pyttsx3
        path=os.path.join(tempfile.gettempdir(),"aig_voice_answer.wav")
        engine=pyttsx3.init(); engine.save_to_file(text,path); engine.runAndWait()
        return path if os.path.exists(path) else None
    except Exception:
        return None
