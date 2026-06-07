import speech_recognition as sr
from gtts import gTTS
import os
import uuid
import re

# We will save audio responses here
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'audio')

if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

def transcribe_audio(audio_path):
    """
    Converts a saved audio file (WAV) into text using Google Web Speech API.
    """
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            # Record the audio data
            audio_data = recognizer.record(source)
            # Transcribe
            text = recognizer.recognize_google(audio_data)
            return text.lower()
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f"Speech Recognition Error: {e}")
        return ""

def determine_intent(text):
    """
    Determine the intent of the doctor's spoken text.
    Returns a dict containing 'intent' and optional extracted data (like 'uid').
    """
    # Intent 1: Show patient risk/history
    history_match = re.search(r"show patient ([\w-]+)", text) or re.search(r"patient ([\w-]+) risk", text)
    if history_match or "show patient" in text or "patient history" in text:
        # Try to extract UID if spoken
        # For simplicity, if they say "patient 101", we might convert to "neo-2026-101" or just search DB
        words = text.split()
        potential_id = ""
        for w in words:
            if any(char.isdigit() for char in w):
                potential_id = w
                break
        return {"intent": "show_history", "uid_context": potential_id}

    # Intent 2: Predict disease risk
    if "predict" in text or "prediction" in text or "evaluate" in text:
        return {"intent": "predict_risk"}

    # Intent 3: Explain prediction results
    if "explain" in text or "why" in text or "importance" in text:
        return {"intent": "explain_prediction"}

    # Intent 4: Latest Dashboard/Alerts
    if "latest" in text or "alerts" in text or "dashboard" in text:
        return {"intent": "latest_alerts"}

    return {"intent": "unknown"}

def generate_voice_response(text):
    """
    Converts a text string to an MP3 audio file using gTTS.
    Returns the filename of the generated audio.
    """
    try:
        filename = f"response_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filepath)
        
        return filename
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

def execute_voice_command(audio_path, app_context_executor):
    """
    Main orchestration function.
    1. Transcribes audio.
    2. Determines intent.
    3. Calls a contextual execution function provided from app.py.
    4. Generates a TTS audio response.
    Returns dict: { 'transcript': str, 'response_text': str, 'audio_url': str }
    """
    transcript = transcribe_audio(audio_path)
    
    if not transcript:
        response_text = "I'm sorry, I couldn't understand that command. Please try again."
        audio_file = generate_voice_response(response_text)
        return {
            "transcript": "...",
            "response_text": response_text,
            "audio_url": f"/static/audio/{audio_file}" if audio_file else None
        }

    intent_data = determine_intent(transcript)
    
    # Execute backend logic based on intent
    response_text = app_context_executor(intent_data, transcript)
    
    audio_file = generate_voice_response(response_text)
    
    return {
        "transcript": transcript,
        "response_text": response_text,
        "audio_url": f"/static/audio/{audio_file}" if audio_file else None
    }
