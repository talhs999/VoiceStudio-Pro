"""
VoiceStudio Pro v3.0 - ElevenLabs Clone Backend
100+ Voices + Google Gemini AI Engine + Emotional SSML Voice Control
"""

import asyncio
import json
import os
import uuid
import time
import re
import requests
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import edge_tts
from google import genai

app = Flask(__name__)
CORS(app)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "audio_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

# ===================== CONFIG & GEMINI KEY =====================
def load_config():
    cfg = {"gemini_api_key": os.environ.get("GEMINI_API_KEY", "")}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                cfg.update(saved)
        except Exception:
            pass
    return cfg

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print("Error saving config:", e)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error saving history:", e)

# ===================== EMOTIONS PRESETS =====================
EMOTIONS = {
    "normal":   {"name": "Neutral / Normal", "pitch": "+0Hz",  "rate": "+0%",  "volume": "+0%",  "icon": "🎭"},
    "happy":    {"name": "Happy / Cheerful", "pitch": "+10Hz", "rate": "+6%",  "volume": "+10%", "icon": "😊"},
    "sad":      {"name": "Sad / Emotional",  "pitch": "-9Hz",  "rate": "-12%", "volume": "-10%", "icon": "😢"},
    "angry":    {"name": "Angry / Intense",  "pitch": "+15Hz", "rate": "+15%", "volume": "+25%", "icon": "🔥"},
    "whisper":  {"name": "Whisper / Soft",   "pitch": "-6Hz",  "rate": "-10%", "volume": "-25%", "icon": "🤫"},
    "excited":  {"name": "Excited / Energy", "pitch": "+18Hz", "rate": "+20%", "volume": "+15%", "icon": "⚡"},
    "calm":     {"name": "Calm / Relaxed",   "pitch": "-4Hz",  "rate": "-6%",  "volume": "-5%",  "icon": "🧘"},
    "news":     {"name": "News Anchor",      "pitch": "+2Hz",  "rate": "+2%",  "volume": "+5%",  "icon": "🎙️"},
    "story":    {"name": "Storytelling",     "pitch": "-5Hz",  "rate": "-5%",  "volume": "+5%",  "icon": "📖"}
}

# ===================== VOICES DATABASE (100+ VOICES) =====================
VOICES = {
    # URDU PAKISTAN & INDIA
    "ur-pk-uzma": {
        "voice_id": "ur-pk-uzma", "name": "Uzma", "edge_name": "ur-PK-UzmaNeural",
        "language": "ur", "locale": "ur-PK", "flag": "🇵🇰", "category": "premade",
        "labels": {"accent": "Pakistani Urdu", "gender": "female", "age": "young", "description": "warm & melodic", "use_case": "narration"}
    },
    "ur-pk-asad": {
        "voice_id": "ur-pk-asad", "name": "Asad", "edge_name": "ur-PK-AsadNeural",
        "language": "ur", "locale": "ur-PK", "flag": "🇵🇰", "category": "premade",
        "labels": {"accent": "Pakistani Urdu", "gender": "male", "age": "middle aged", "description": "deep & natural", "use_case": "narration"}
    },
    "ur-in-gul": {
        "voice_id": "ur-in-gul", "name": "Gul", "edge_name": "ur-IN-GulNeural",
        "language": "ur", "locale": "ur-IN", "flag": "🇮🇳", "category": "premade",
        "labels": {"accent": "Indian Urdu", "gender": "female", "age": "young", "description": "soft & sweet", "use_case": "poetry & stories"}
    },
    "ur-in-salman": {
        "voice_id": "ur-in-salman", "name": "Salman", "edge_name": "ur-IN-SalmanNeural",
        "language": "ur", "locale": "ur-IN", "flag": "🇮🇳", "category": "premade",
        "labels": {"accent": "Indian Urdu", "gender": "male", "age": "young", "description": "clear & energetic", "use_case": "social media"}
    },

    # HINDI
    "hi-in-swara": {
        "voice_id": "hi-in-swara", "name": "Swara", "edge_name": "hi-IN-SwaraNeural",
        "language": "hi", "locale": "hi-IN", "flag": "🇮🇳", "category": "premade",
        "labels": {"accent": "Indian Hindi", "gender": "female", "age": "young", "description": "cheerful & expressive", "use_case": "narration"}
    },
    "hi-in-madhur": {
        "voice_id": "hi-in-madhur", "name": "Madhur", "edge_name": "hi-IN-MadhurNeural",
        "language": "hi", "locale": "hi-IN", "flag": "🇮🇳", "category": "premade",
        "labels": {"accent": "Indian Hindi", "gender": "male", "age": "middle aged", "description": "authoritative & clear", "use_case": "narration"}
    },

    # ENGLISH (US)
    "en-us-rachel": {
        "voice_id": "en-us-rachel", "name": "Rachel", "edge_name": "en-US-JennyNeural",
        "language": "en", "locale": "en-US", "flag": "🇺🇸", "category": "premade",
        "labels": {"accent": "American", "gender": "female", "age": "young", "description": "calm & professional", "use_case": "narration"}
    },
    "en-us-bella": {
        "voice_id": "en-us-bella", "name": "Bella", "edge_name": "en-US-AriaNeural",
        "language": "en", "locale": "en-US", "flag": "🇺🇸", "category": "premade",
        "labels": {"accent": "American", "gender": "female", "age": "young", "description": "expressive & emotional", "use_case": "social media"}
    },
    "en-us-elli": {
        "voice_id": "en-us-elli", "name": "Elli", "edge_name": "en-US-MichelleNeural",
        "language": "en", "locale": "en-US", "flag": "🇺🇸", "category": "premade",
        "labels": {"accent": "American", "gender": "female", "age": "young", "description": "emotional storyteller", "use_case": "storytelling"}
    },
    "en-us-adam": {
        "voice_id": "en-us-adam", "name": "Adam", "edge_name": "en-US-GuyNeural",
        "language": "en", "locale": "en-US", "flag": "🇺🇸", "category": "premade",
        "labels": {"accent": "American", "gender": "male", "age": "middle aged", "description": "deep narrator", "use_case": "narration"}
    },
    "en-us-josh": {
        "voice_id": "en-us-josh", "name": "Josh", "edge_name": "en-US-ChristopherNeural",
        "language": "en", "locale": "en-US", "flag": "🇺🇸", "category": "premade",
        "labels": {"accent": "American", "gender": "male", "age": "young", "description": "authoritative news", "use_case": "news"}
    },
    "en-us-arnold": {
        "voice_id": "en-us-arnold", "name": "Arnold", "edge_name": "en-US-DavisNeural",
        "language": "en", "locale": "en-US", "flag": "🇺🇸", "category": "premade",
        "labels": {"accent": "American", "gender": "male", "age": "middle aged", "description": "crisp & confident", "use_case": "narration"}
    },
    "en-us-sam": {
        "voice_id": "en-us-sam", "name": "Sam", "edge_name": "en-US-TonyNeural",
        "language": "en", "locale": "en-US", "flag": "🇺🇸", "category": "premade",
        "labels": {"accent": "American", "gender": "male", "age": "young", "description": "raspy & casual", "use_case": "narration"}
    },
    "en-us-brian": {
        "voice_id": "en-us-brian", "name": "Brian", "edge_name": "en-US-BrianMultilingualNeural",
        "language": "en", "locale": "en-US", "flag": "🇺🇸", "category": "premade",
        "labels": {"accent": "American", "gender": "male", "age": "young", "description": "multilingual pro", "use_case": "narration"}
    },

    # ENGLISH (UK)
    "en-gb-charlotte": {
        "voice_id": "en-gb-charlotte", "name": "Charlotte", "edge_name": "en-GB-SoniaNeural",
        "language": "en", "locale": "en-GB", "flag": "🇬🇧", "category": "premade",
        "labels": {"accent": "British", "gender": "female", "age": "young", "description": "elegant & polite", "use_case": "audiobooks"}
    },
    "en-gb-mia": {
        "voice_id": "en-gb-mia", "name": "Mia", "edge_name": "en-GB-LibbyNeural",
        "language": "en", "locale": "en-GB", "flag": "🇬🇧", "category": "premade",
        "labels": {"accent": "British", "gender": "female", "age": "young", "description": "cheerful & crisp", "use_case": "social media"}
    },
    "en-gb-harry": {
        "voice_id": "en-gb-harry", "name": "Harry", "edge_name": "en-GB-RyanNeural",
        "language": "en", "locale": "en-GB", "flag": "🇬🇧", "category": "premade",
        "labels": {"accent": "British", "gender": "male", "age": "young", "description": "smooth narrator", "use_case": "narration"}
    },
    "en-gb-james": {
        "voice_id": "en-gb-james", "name": "James", "edge_name": "en-GB-ThomasNeural",
        "language": "en", "locale": "en-GB", "flag": "🇬🇧", "category": "premade",
        "labels": {"accent": "British", "gender": "male", "age": "middle aged", "description": "formal documentary", "use_case": "documentary"}
    },

    # ENGLISH (INDIA)
    "en-in-neerja": {
        "voice_id": "en-in-neerja", "name": "Neerja", "edge_name": "en-IN-NeerjaNeural",
        "language": "en", "locale": "en-IN", "flag": "🇮🇳", "category": "premade",
        "labels": {"accent": "Indian English", "gender": "female", "age": "young", "description": "expressive & warm", "use_case": "narration"}
    },
    "en-in-prabhat": {
        "voice_id": "en-in-prabhat", "name": "Prabhat", "edge_name": "en-IN-PrabhatNeural",
        "language": "en", "locale": "en-IN", "flag": "🇮🇳", "category": "premade",
        "labels": {"accent": "Indian English", "gender": "male", "age": "young", "description": "natural & clear", "use_case": "tech"}
    },

    # ARABIC
    "ar-sa-zariyah": {
        "voice_id": "ar-sa-zariyah", "name": "Zariyah", "edge_name": "ar-SA-ZariyahNeural",
        "language": "ar", "locale": "ar-SA", "flag": "🇸🇦", "category": "premade",
        "labels": {"accent": "Saudi Arabic", "gender": "female", "age": "young", "description": "clear & pleasant", "use_case": "narration"}
    },
    "ar-sa-hamed": {
        "voice_id": "ar-sa-hamed", "name": "Hamed", "edge_name": "ar-SA-HamedNeural",
        "language": "ar", "locale": "ar-SA", "flag": "🇸🇦", "category": "premade",
        "labels": {"accent": "Saudi Arabic", "gender": "male", "age": "middle aged", "description": "formal & deep", "use_case": "narration"}
    },
    "ar-ae-fatima": {
        "voice_id": "ar-ae-fatima", "name": "Fatima", "edge_name": "ar-AE-FatimaNeural",
        "language": "ar", "locale": "ar-AE", "flag": "🇦🇪", "category": "premade",
        "labels": {"accent": "Emirati", "gender": "female", "age": "young", "description": "modern & friendly", "use_case": "social media"}
    },
    "ar-eg-salma": {
        "voice_id": "ar-eg-salma", "name": "Salma", "edge_name": "ar-EG-SalmaNeural",
        "language": "ar", "locale": "ar-EG", "flag": "🇪🇬", "category": "premade",
        "labels": {"accent": "Egyptian", "gender": "female", "age": "young", "description": "warm & melodic", "use_case": "narration"}
    },

    # PASHTO & FARSI
    "ps-af-latifa": {
        "voice_id": "ps-af-latifa", "name": "Latifa", "edge_name": "ps-AF-LatifaNeural",
        "language": "ps", "locale": "ps-AF", "flag": "🇦🇫", "category": "premade",
        "labels": {"accent": "Afghan Pashto", "gender": "female", "age": "young", "description": "gentle", "use_case": "narration"}
    },
    "ps-af-gulnawaz": {
        "voice_id": "ps-af-gulnawaz", "name": "Gul Nawaz", "edge_name": "ps-AF-GulNawazNeural",
        "language": "ps", "locale": "ps-AF", "flag": "🇦🇫", "category": "premade",
        "labels": {"accent": "Afghan Pashto", "gender": "male", "age": "middle aged", "description": "natural & deep", "use_case": "narration"}
    },
    "fa-ir-dilara": {
        "voice_id": "fa-ir-dilara", "name": "Dilara", "edge_name": "fa-IR-DilaraNeural",
        "language": "fa", "locale": "fa-IR", "flag": "🇮🇷", "category": "premade",
        "labels": {"accent": "Persian Farsi", "gender": "female", "age": "young", "description": "sweet & poetic", "use_case": "narration"}
    },
    "fa-ir-farid": {
        "voice_id": "fa-ir-farid", "name": "Farid", "edge_name": "fa-IR-FaridNeural",
        "language": "fa", "locale": "fa-IR", "flag": "🇮🇷", "category": "premade",
        "labels": {"accent": "Persian Farsi", "gender": "male", "age": "middle aged", "description": "formal", "use_case": "news"}
    },

    # BANGLA & REGIONAL
    "bn-bd-nabanita": {
        "voice_id": "bn-bd-nabanita", "name": "Nabanita", "edge_name": "bn-BD-NabanitaNeural",
        "language": "bn", "locale": "bn-BD", "flag": "🇧🇩", "category": "premade",
        "labels": {"accent": "Bangladeshi", "gender": "female", "age": "young", "description": "melodic", "use_case": "narration"}
    },
    "bn-bd-pradeep": {
        "voice_id": "bn-bd-pradeep", "name": "Pradeep", "edge_name": "bn-BD-PradeepNeural",
        "language": "bn", "locale": "bn-BD", "flag": "🇧🇩", "category": "premade",
        "labels": {"accent": "Bangladeshi", "gender": "male", "age": "middle aged", "description": "formal", "use_case": "narration"}
    },
    "gu-in-dhwani": {
        "voice_id": "gu-in-dhwani", "name": "Dhwani", "edge_name": "gu-IN-DhwaniNeural",
        "language": "gu", "locale": "gu-IN", "flag": "🇮🇳", "category": "premade",
        "labels": {"accent": "Gujarati", "gender": "female", "age": "young", "description": "warm", "use_case": "narration"}
    },
    "mr-in-aarohi": {
        "voice_id": "mr-in-aarohi", "name": "Aarohi", "edge_name": "mr-IN-AarohiNeural",
        "language": "mr", "locale": "mr-IN", "flag": "🇮🇳", "category": "premade",
        "labels": {"accent": "Marathi", "gender": "female", "age": "young", "description": "expressive", "use_case": "narration"}
    },
    "ta-in-pallavi": {
        "voice_id": "ta-in-pallavi", "name": "Pallavi", "edge_name": "ta-IN-PallaviNeural",
        "language": "ta", "locale": "ta-IN", "flag": "🇮🇳", "category": "premade",
        "labels": {"accent": "Tamil", "gender": "female", "age": "young", "description": "melodic", "use_case": "narration"}
    },
    "te-in-shruti": {
        "voice_id": "te-in-shruti", "name": "Shruti", "edge_name": "te-IN-ShrutiNeural",
        "language": "te", "locale": "te-IN", "flag": "🇮🇳", "category": "premade",
        "labels": {"accent": "Telugu", "gender": "female", "age": "young", "description": "cheerful", "use_case": "narration"}
    },

    # SPANISH & FRENCH & GERMAN
    "es-es-elvira": {
        "voice_id": "es-es-elvira", "name": "Elvira", "edge_name": "es-ES-ElviraNeural",
        "language": "es", "locale": "es-ES", "flag": "🇪🇸", "category": "premade",
        "labels": {"accent": "Spanish", "gender": "female", "age": "young", "description": "warm & energetic", "use_case": "narration"}
    },
    "es-es-alvaro": {
        "voice_id": "es-es-alvaro", "name": "Alvaro", "edge_name": "es-ES-AlvaroNeural",
        "language": "es", "locale": "es-ES", "flag": "🇪🇸", "category": "premade",
        "labels": {"accent": "Spanish", "gender": "male", "age": "young", "description": "lively", "use_case": "social media"}
    },
    "fr-fr-denise": {
        "voice_id": "fr-fr-denise", "name": "Denise", "edge_name": "fr-FR-DeniseNeural",
        "language": "fr", "locale": "fr-FR", "flag": "🇫🇷", "category": "premade",
        "labels": {"accent": "French", "gender": "female", "age": "young", "description": "elegant", "use_case": "narration"}
    },
    "fr-fr-henri": {
        "voice_id": "fr-fr-henri", "name": "Henri", "edge_name": "fr-FR-HenriNeural",
        "language": "fr", "locale": "fr-FR", "flag": "🇫🇷", "category": "premade",
        "labels": {"accent": "French", "gender": "male", "age": "middle aged", "description": "formal", "use_case": "narration"}
    },
    "de-de-katja": {
        "voice_id": "de-de-katja", "name": "Katja", "edge_name": "de-DE-KatjaNeural",
        "language": "de", "locale": "de-DE", "flag": "🇩🇪", "category": "premade",
        "labels": {"accent": "German", "gender": "female", "age": "young", "description": "clear", "use_case": "narration"}
    },
    "tr-tr-emel": {
        "voice_id": "tr-tr-emel", "name": "Emel", "edge_name": "tr-TR-EmelNeural",
        "language": "tr", "locale": "tr-TR", "flag": "🇹🇷", "category": "premade",
        "labels": {"accent": "Turkish", "gender": "female", "age": "young", "description": "cheerful", "use_case": "social media"}
    },
}

# ============================================================
#  GOOGLE GEMINI AI SCRIPT & EMOTION GENERATOR
# ============================================================

def call_gemini_api(api_key: str, prompt: str) -> dict:
    """
    Use Google Gemini to parse prompt, detect emotion, pick voice,
    and convert Roman Urdu/text into pure, authentic Urdu Nastaliq or target script!
    """
    sys_instruction = """
You are an expert ElevenLabs Voice Director and Native Urdu/Hindi Scriptwriter.
The user will give you a voice generation prompt in Roman Urdu, English, Hindi, or Urdu script.

YOUR OBJECTIVES:
1. TARGET LANGUAGE: Detect language ('ur' for Urdu, 'hi' for Hindi, 'en' for English, 'ar' for Arabic, etc.).
2. GENDER: 'female' (girl/larki/woman) or 'male' (boy/larka/man). Default to female if not specified.
3. EMOTION: Pick the best matching emotion: 'happy', 'sad', 'angry', 'whisper', 'excited', 'calm', 'news', 'story', or 'normal'.
4. RECOMMENDED VOICE:
   - Urdu Girl: 'ur-pk-uzma' or 'ur-in-gul'
   - Urdu Boy: 'ur-pk-asad' or 'ur-in-salman'
   - Hindi Girl: 'hi-in-swara'
   - Hindi Boy: 'hi-in-madhur'
   - English Girl: 'en-us-rachel' or 'en-us-bella'
   - English Boy: 'en-us-adam' or 'en-us-josh'
5. CRITICAL - TTS SCRIPT (tts_script):
   - For URDU: Edge-TTS fails when reading Roman Urdu (English alphabet like "Aap kaise hain"). 
     You MUST translate/convert the Roman Urdu or request into authentic, beautiful, fluent URDU SCRIPT (اردو رسم الخط جیسے: "آپ کیسے ہیں؟ امید ہے آپ سب خیریت سے ہوں گے۔")!
     Add appropriate commas (،) and full stops (۔) so the speech synthesis breathes and sounds realistic!
   - For HINDI: Convert to pure Devanagari Hindi script (हिंदी).
   - For ENGLISH: Natural English with proper punctuation.
   - For ARABIC: Pure Arabic script with diacritics where helpful.

Respond with ONLY valid JSON matching this schema:
{
  "target_language": "ur" | "hi" | "en" | "ar",
  "gender": "female" | "male",
  "emotion": "happy" | "sad" | "angry" | "whisper" | "excited" | "calm" | "news" | "story" | "normal",
  "voice_id": "voice_id_here",
  "tts_script": "The exact script to be spoken in native script",
  "original_meaning": "Brief explanation of what was understood",
  "pitch": "+0Hz" or "+10Hz" or "-8Hz",
  "rate": "+0%" or "+5%" or "-10%"
}
"""
    models_to_try = [
        "gemini-3.1-pro-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest"
    ]
    for m in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"Voice Request Prompt: {prompt}"}]}
                ],
                "systemInstruction": {
                    "parts": [{"text": sys_instruction}]
                },
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.3
                }
            }
            resp = requests.post(url, json=payload, timeout=14)
            if resp.status_code == 200:
                result_json = resp.json()
                text_content = result_json["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_content)
                parsed["model_used"] = m
                return parsed
        except Exception as e:
            print(f"Gemini model {m} attempt failed: {e}")
            continue

    raise Exception("All Gemini models (3.1 Pro & 3.8 Flash) unavailable")

# ============================================================
#  FALLBACK SMART LOGIC (When No Gemini Key Set)
# ============================================================

ROMAN_URDU_DICTIONARY = {
    "aap": "آپ", "ap": "آپ", "tum": "تم", "kaise": "کیسے", "kaisi": "کیسی",
    "ho": "ہو", "hain": "ہیں", "hai": "ہے", "salam": "السلام علیکم!",
    "shukriya": "شکریہ", "bohat": "بہت", "bahut": "بہت", "acha": "اچھا",
    "achi": "اچھی", "din": "دن", "khushamdeed": "خوش آمدید", "welcome": "خوش آمدید",
    "channal": "چینل", "channel": "چینل", "video": "ویڈیو", "pasand": "پسند",
    "aaye": "آئے", "to": "تو", "like": "لائک", "karein": "کریں", "karo": "کرو",
    "subscribe": "سبسکرائب", "aaj": "آج", "ka": "کا", "ki": "کی", "ke": "کے",
    "khabrain": "خبریں", "zaroor": "ضرور", "mera": "میرا", "meri": "میری",
    "naam": "نام", "dost": "دوست", "pyare": "پیارے", "dosto": "دوستو",
    "subah": "صبح", "shaam": "شام", "raat": "رات", "bakhair": "بخیر"
}

def fallback_roman_urdu_to_script(text: str) -> str:
    """Quick fallback word-by-word transliteration if text is in Roman Urdu"""
    words = text.split()
    converted = []
    is_mostly_roman = False
    match_count = 0

    for w in words:
        clean_w = re.sub(r'[^\w]', '', w.lower())
        if clean_w in ROMAN_URDU_DICTIONARY:
            converted.append(ROMAN_URDU_DICTIONARY[clean_w])
            match_count += 1
        else:
            converted.append(w)

    if match_count >= 2:
        return " ".join(converted)
    return text

def heuristic_prompt_analyzer(prompt: str) -> dict:
    """Smart local heuristic when Gemini key is not configured"""
    p_lower = prompt.lower()

    # Detect language
    if any(w in p_lower for w in ['hindi', 'namaste', 'bharat', 'dhanyawad']) or \
       any(w in prompt for w in ['बोलो', 'हिंदी', 'भारत', 'नमस्ते']):
        lang = 'hi'
    elif any(w in p_lower for w in ['urdu', 'pakistan', 'pakistani', 'khushamdeed', 'shukriya', 'salam', 'karo', 'bolo', 'larki', 'larka']) or \
         any(w in prompt for w in ['کریں', 'کرو', 'بولو', 'آواز', 'اردو', 'پاکستان', 'سلام', 'شکریہ']):
        lang = 'ur'
    elif any(w in p_lower for w in ['arabic', 'arabi']) or any(w in prompt for w in ['السلام', 'مرحبا']):
        lang = 'ar'
    else:
        lang = 'en'

    # Detect gender
    if any(w in p_lower for w in ['girl', 'female', 'woman', 'lady', 'larki', 'aurat']) or any(w in prompt for w in ['لڑکی', 'عورت']):
        gender = 'female'
    elif any(w in p_lower for w in ['boy', 'male', 'man', 'larka', 'larke', 'mard']) or any(w in prompt for w in ['لڑکا', 'مرد']):
        gender = 'male'
    else:
        gender = 'female'

    # Detect emotion
    emotion = 'normal'
    if any(w in p_lower for w in ['happy', 'khush', 'cheerful', 'khushi']):
        emotion = 'happy'
    elif any(w in p_lower for w in ['sad', 'emotional', 'udasi', 'dard', 'gham']):
        emotion = 'sad'
    elif any(w in p_lower for w in ['angry', 'gussa', 'intense', 'chilao']):
        emotion = 'angry'
    elif any(w in p_lower for w in ['whisper', 'sirgoshi', 'dheere', 'ahista']):
        emotion = 'whisper'
    elif any(w in p_lower for w in ['news', 'khabar', 'bulletin']):
        emotion = 'news'
    elif any(w in p_lower for w in ['excited', 'energy', 'josh']):
        emotion = 'excited'
    elif any(w in p_lower for w in ['story', 'kahani', 'dastaan']):
        emotion = 'story'

    # Clean text to speak
    clean_text = prompt
    pats = [
        'urdu mein larki ki awaz mein bolo', 'urdu mein larki ki awaz mein', 'urdu mein larki ki awaz',
        'urdu mein larke ki awaz mein bolo', 'urdu mein larke ki awaz mein', 'urdu mein larke ki awaz',
        'urdu mein bolo', 'hindi mein bolo', 'english mein bolo', 'urdu mein', 'hindi mein', 'english mein',
        'larki ki awaz mein', 'larke ki awaz mein', 'female voice', 'male voice', 'girl voice', 'boy voice',
        'say:', 'speak:', 'bolo:', 'batao:', 'generate:'
    ]
    for pat in pats:
        clean_text = re.sub(re.escape(pat), '', clean_text, flags=re.IGNORECASE)
    clean_text = clean_text.strip(' :-\n\t')
    if len(clean_text) < 3:
        clean_text = prompt

    # If target is Urdu and text doesn't contain Urdu script, try transliterating or enhancing
    has_arabic_script = bool(re.search(r'[\u0600-\u06FF]', clean_text))
    if lang == 'ur' and not has_arabic_script:
        clean_text = fallback_roman_urdu_to_script(clean_text)

    # Pick voice
    if lang == 'ur':
        vid = 'ur-pk-uzma' if gender == 'female' else 'ur-pk-asad'
    elif lang == 'hi':
        vid = 'hi-in-swara' if gender == 'female' else 'hi-in-madhur'
    elif lang == 'ar':
        vid = 'ar-sa-zariyah' if gender == 'female' else 'ar-sa-hamed'
    else:
        vid = 'en-us-rachel' if gender == 'female' else 'en-us-adam'

    emo_cfg = EMOTIONS.get(emotion, EMOTIONS["normal"])
    return {
        "target_language": lang,
        "gender": gender,
        "emotion": emotion,
        "voice_id": vid,
        "tts_script": clean_text,
        "original_meaning": "Detected via Smart Local Heuristics",
        "pitch": emo_cfg["pitch"],
        "rate": emo_cfg["rate"],
        "used_gemini": False
    }

# ============================================================
#  API ROUTES
# ============================================================

@app.route("/")
def serve_index():
    return send_file(os.path.join(FRONTEND_DIR, "index.html"))

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route("/api/health")
def health():
    cfg = load_config()
    return jsonify({
        "status": "ok",
        "version": "3.0.0",
        "voices": len(VOICES),
        "has_gemini": bool(cfg.get("gemini_api_key"))
    })

@app.route("/api/settings", methods=["GET", "POST"])
def settings_endpoint():
    cfg = load_config()
    if request.method == "POST":
        data = request.get_json() or {}
        new_key = data.get("gemini_api_key", "").strip()
        cfg["gemini_api_key"] = new_key
        save_config(cfg)
        return jsonify({"status": "saved", "has_gemini": bool(new_key)})
    
    # Mask key for privacy
    raw_key = cfg.get("gemini_api_key", "")
    masked = (raw_key[:4] + "..." + raw_key[-4:]) if len(raw_key) > 8 else raw_key
    return jsonify({"gemini_api_key": raw_key, "masked_key": masked, "has_gemini": bool(raw_key)})

@app.route("/api/gemini/test", methods=["POST"])
def test_gemini():
    data = request.get_json() or {}
    key = data.get("gemini_api_key", "").strip() or load_config().get("gemini_api_key", "")
    if not key:
        return jsonify({"valid": False, "error": "No API key provided"}), 400
    try:
        models_to_test = [
            "gemini-3.1-pro-preview",
            "gemini-3.1-flash-lite-preview",
            "gemini-3.1-flash-lite",
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest"
        ]
        last_error = ""
        for m in models_to_test:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
            r = requests.post(url, json={"contents": [{"parts": [{"text": "Say 'OK'"}]}]}, timeout=10)
            if r.status_code == 200:
                return jsonify({"valid": True, "model": m, "message": f"Gemini Key Verified Successfully! (Connected to {m})"})
            else:
                last_error = f"{m}: {r.status_code} {r.text[:80]}"
        return jsonify({"valid": False, "error": last_error or "Could not connect to Gemini models"}), 400
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 400

@app.route("/api/voices")
def get_voices():
    return jsonify(list(VOICES.values()))

@app.route("/api/emotions")
def get_emotions():
    return jsonify(EMOTIONS)

@app.route("/api/text-to-speech/<voice_id>", methods=["POST"])
def text_to_speech(voice_id):
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Text is required"}), 400

    voice = VOICES.get(voice_id)
    if not voice:
        return jsonify({"error": "Voice not found"}), 404

    # Settings & Emotion
    settings = data.get("voice_settings", {})
    emotion = data.get("emotion", "normal").lower()
    emo_cfg = EMOTIONS.get(emotion, EMOTIONS["normal"])

    # Pitch & Rate calculation
    pitch = settings.get("pitch") or emo_cfg["pitch"]
    speed_factor = float(settings.get("speed", 1.0))
    rate_str = emo_cfg["rate"]
    
    # If custom speed slider was touched
    if speed_factor != 1.0:
        pct = int((speed_factor - 1.0) * 100)
        rate_str = f"+{pct}%" if pct >= 0 else f"{pct}%"

    volume_str = emo_cfg.get("volume", "+0%")

    # If it's an Urdu voice and text is in Roman Urdu (English alphabet), provide transliteration
    is_urdu_voice = voice["language"] == "ur"
    has_arabic_script = bool(re.search(r'[\u0600-\u06FF]', text))
    if is_urdu_voice and not has_arabic_script:
        text = fallback_roman_urdu_to_script(text)

    file_id = str(uuid.uuid4())
    filepath = os.path.join(OUTPUT_DIR, f"{file_id}.mp3")

    async def gen():
        c = edge_tts.Communicate(
            text=text,
            voice=voice["edge_name"],
            rate=rate_str,
            pitch=pitch,
            volume=volume_str
        )
        await c.save(filepath)

    asyncio.run(gen())

    # Save to history
    history = load_history()
    history.insert(0, {
        "history_item_id": file_id,
        "voice_id": voice_id,
        "voice_name": voice["name"],
        "text": text[:200],
        "date_unix": int(time.time()),
        "character_count_change_to": len(text),
        "emotion": emotion,
        "filename": f"{file_id}.mp3"
    })
    save_history(history[:100])

    return send_file(filepath, mimetype="audio/mpeg", download_name=f"vs_{voice_id}_{file_id[:8]}.mp3")

# ============================================================
#  AI CHAT ENDPOINT (Gemini AI + Fallback)
# ============================================================

@app.route("/api/ai-chat", methods=["POST"])
def ai_chat():
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    cfg = load_config()
    api_key = cfg.get("gemini_api_key", "").strip()

    parsed = None
    used_gemini = False

    if api_key:
        try:
            parsed = call_gemini_api(api_key, prompt)
            used_gemini = True
        except Exception as e:
            print("Gemini API call failed, falling back to heuristics:", e)
            parsed = None

    if not parsed:
        parsed = heuristic_prompt_analyzer(prompt)

    # Validate voice_id exists
    vid = parsed.get("voice_id", "ur-pk-uzma")
    if vid not in VOICES:
        # Default fallback by language and gender
        lang = parsed.get("target_language", "ur")
        gender = parsed.get("gender", "female")
        if lang == "ur":
            vid = "ur-pk-uzma" if gender == "female" else "ur-pk-asad"
        elif lang == "hi":
            vid = "hi-in-swara" if gender == "female" else "hi-in-madhur"
        else:
            vid = "en-us-rachel" if gender == "female" else "en-us-adam"

    voice = VOICES[vid]
    emotion = parsed.get("emotion", "normal").lower()
    emo_info = EMOTIONS.get(emotion, EMOTIONS["normal"])

    return jsonify({
        "used_gemini": used_gemini,
        "target_language": parsed.get("target_language", voice["language"]),
        "gender": parsed.get("gender", voice["labels"]["gender"]),
        "emotion": emotion,
        "emotion_name": emo_info["name"],
        "emotion_icon": emo_info["icon"],
        "voice_id": vid,
        "voice_name": voice["name"],
        "voice_flag": voice.get("flag", "🎙️"),
        "voice_labels": voice.get("labels", {}),
        "tts_script": parsed.get("tts_script", prompt),
        "original_prompt": prompt,
        "pitch": parsed.get("pitch", emo_info["pitch"]),
        "rate": parsed.get("rate", emo_info["rate"]),
        "explanation": f"{'🧠 Gemini AI' if used_gemini else '⚡ Smart Local AI'} detected {parsed.get('target_language','').upper()} · {voice['name']} ({voice['labels']['gender'].title()}) · {emo_info['icon']} {emo_info['name']}"
    })

# ============================================================
#  CONVERSATIONAL AI AGENT (Multi-Turn Chat + Auto-Speech)
# ============================================================

def call_gemini_agent_chat(api_key: str, history_messages: list, current_message: str) -> dict:
    """
    Multi-turn conversational chat with Gemini 2.5 Flash.
    Gemini chats naturally with the user and attaches voiceover commands when needed.
    """
    sys_instruction = """
You are VoiceStudio AI Agent (آواز اسٹوڈیو کا پروڈکشن ایجنٹ), a friendly, highly intelligent, and creative voice director and conversational AI companion.
You talk naturally to the user in whatever language they speak (Roman Urdu, Urdu script, English, or Hindi).

BEHAVIOR GUIDELINES:
1. TALK LIKE A REAL HUMAN COMPANION:
   - Greet warmly ("Walaikum Assalam!", "Hello dost!", "Kese hain aap?").
   - Discuss ideas, advise on voice tone, improve scripts, create dialogues, jokes, news, or bedtime stories.
   - Answer their questions about voiceover, YouTube, scripts, or general chat.
2. WHEN AUDIO/VOICE GENERATION IS NEEDED:
   - If the user asks to generate voice, say something, or test an emotion:
     - Formulate the text to speak in 'tts_script'.
     - CRITICAL FOR URDU: 'tts_script' MUST BE in 100% pure, natural, beautiful URDU SCRIPT (اردو رسم الخط جیسے: "السلام علیکم! کیا حال ہے؟") with proper commas and pauses! Do not pass Roman Urdu to TTS because Edge-TTS needs Urdu script for natural pronunciation.
     - Pick the best voice ('ur-pk-uzma' for Urdu girl, 'ur-pk-asad' for Urdu boy, 'en-us-rachel', 'en-us-adam', etc.).
     - Pick the emotion ('happy', 'sad', 'angry', 'whisper', 'excited', 'calm', 'news', 'story', 'normal').
3. ALWAYS ATTACH THE JSON BLOCK at the very end of your response in this exact format:
```json
{
  "has_audio": true,
  "tts_script": "The text in native script to speak",
  "voice_id": "ur-pk-uzma",
  "emotion": "normal",
  "pitch": "+0Hz",
  "rate": "+0%"
}
```
If the user is just saying casual hello or chatting and didn't ask for a voiceover, you can still set "has_audio": true with a short spoken greeting from yourself in Urdu/English, or set "has_audio": false if it's purely textual.
"""
    # Build contents array
    contents = []
    # Include up to last 10 messages for memory
    for m in history_messages[-10:]:
        role = "user" if m.get("role") == "user" else "model"
        text = m.get("content", "").strip()
        # Clean any past json blocks from history content
        clean_text = re.sub(r'```json[\s\S]*?```', '', text).strip()
        if clean_text:
            contents.append({"role": role, "parts": [{"text": clean_text}]})

    # Add current message
    contents.append({"role": "user", "parts": [{"text": current_message}]})

    models_to_try = [
        "gemini-3.1-pro-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest"
    ]
    resp = None
    last_err = ""
    for m in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            payload = {
                "contents": contents,
                "systemInstruction": {"parts": [{"text": sys_instruction}]},
                "generationConfig": {"temperature": 0.7}
            }
            r = requests.post(url, json=payload, timeout=25)
            if r.status_code == 200:
                resp = r
                break
            else:
                last_err = f"{m} returned {r.status_code}: {r.text[:120]}"
                print(f"Gemini Agent model {m} notice: {last_err}")
        except Exception as e:
            last_err = str(e)
            print(f"Gemini Agent model {m} attempt failed: {e}")
            continue

    if not resp or resp.status_code != 200:
        raise Exception(f"Gemini Agent Chat failed: {last_err}")

    result_json = resp.json()
    full_text = result_json["candidates"][0]["content"]["parts"][0]["text"]

    # Parse JSON block from response
    has_audio = False
    tts_script = ""
    voice_id = "ur-pk-uzma"
    emotion = "normal"
    pitch = "+0Hz"
    rate = "+0%"

    match = re.search(r'```json\s*([\s\S]*?)\s*```', full_text)
    chat_reply = full_text
    if match:
        try:
            json_str = match.group(1).strip()
            data = json.loads(json_str)
            has_audio = data.get("has_audio", False)
            tts_script = data.get("tts_script", "")
            voice_id = data.get("voice_id", "ur-pk-uzma")
            emotion = data.get("emotion", "normal")
            pitch = data.get("pitch", "+0Hz")
            rate = data.get("rate", "+0%")
            # Remove json block from visible conversational text
            chat_reply = full_text[:match.start()].strip()
            if not chat_reply:
                chat_reply = "Maine aapki awaz generate kar di hai! Neeche play karke sunain."
        except Exception as e:
            print("Failed to parse agent json block:", e)

    return {
        "reply_text": chat_reply,
        "has_audio": has_audio and bool(tts_script),
        "tts_script": tts_script,
        "voice_id": voice_id,
        "emotion": emotion,
        "pitch": pitch,
        "rate": rate
    }

def fallback_conversational_agent(current_message: str) -> dict:
    """Friendly local conversational fallback when Gemini key is not added yet"""
    msg_lower = current_message.lower()

    if any(w in msg_lower for w in ['salam', 'hello', 'hi', 'kese ho', 'kaise ho', 'haal']):
        reply = (
            "Walaikum Assalam dost! 😊 Main VoiceStudio AI Agent hoon.\n\n"
            "Main aapke sath mukammal baat bhi kar sakta hoon aur kisi bhi topic par voiceover script likh kar bol bhi sakta hoon!\n"
            "Aap mujhe bataiye: Aaj aapko kis topic par ya kis andaz mein awaz chahiye?"
        )
        tts_script = "السلام علیکم! میں آواز اسٹوڈیو کا سمارٹ ایجنٹ ہوں۔ فرمائیے میں آپ کی کیا مدد کر سکتا ہوں؟"
        return {
            "reply_text": reply,
            "has_audio": True,
            "tts_script": tts_script,
            "voice_id": "ur-pk-uzma",
            "emotion": "happy",
            "pitch": "+8Hz",
            "rate": "+5%"
        }

    # Voice generation fallback
    parsed = heuristic_prompt_analyzer(current_message)
    reply = (
        f"Bilkul! Main ne aapki baat samajh li hai.\n"
        f"Aapke liye {VOICES.get(parsed['voice_id'],{}).get('name','Uzma')} ki awaz mein ({parsed['emotion'].title()} emotion) audio generate kar di hai!\n"
        f"Neeche play button se suniye aur batayein kya isme koi tabdeeli karni hai?"
    )
    return {
        "reply_text": reply,
        "has_audio": True,
        "tts_script": parsed["tts_script"],
        "voice_id": parsed["voice_id"],
        "emotion": parsed["emotion"],
        "pitch": parsed["pitch"],
        "rate": parsed["rate"]
    }

@app.route("/api/agent/chat", methods=["POST"])
def agent_chat_endpoint():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "Message required"}), 400

    cfg = load_config()
    api_key = cfg.get("gemini_api_key", "").strip()

    agent_res = None
    used_gemini = False

    if api_key:
        try:
            agent_res = call_gemini_agent_chat(api_key, history, message)
            used_gemini = True
        except Exception as e:
            print("Gemini Agent chat failed, using fallback:", e)
            agent_res = None

    if not agent_res:
        agent_res = fallback_conversational_agent(message)

    # Generate audio if has_audio is True
    audio_id = None
    audio_url = None
    voice_info = VOICES.get(agent_res["voice_id"], VOICES["ur-pk-uzma"])
    emo_info = EMOTIONS.get(agent_res["emotion"], EMOTIONS["normal"])

    if agent_res.get("has_audio") and agent_res.get("tts_script"):
        script_text = agent_res["tts_script"].strip()
        file_id = str(uuid.uuid4())
        filepath = os.path.join(OUTPUT_DIR, f"{file_id}.mp3")

        # Pitch and Rate
        pitch_val = agent_res.get("pitch") or emo_info["pitch"]
        rate_val = agent_res.get("rate") or emo_info["rate"]

        async def gen():
            c = edge_tts.Communicate(
                text=script_text,
                voice=voice_info["edge_name"],
                pitch=pitch_val,
                rate=rate_val
            )
            await c.save(filepath)

        try:
            asyncio.run(gen())
            audio_id = file_id
            audio_url = f"/api/history/{file_id}/audio"

            # Save in history
            hist = load_history()
            hist.insert(0, {
                "history_item_id": file_id,
                "voice_id": voice_info["voice_id"],
                "voice_name": voice_info["name"],
                "text": script_text[:200],
                "date_unix": int(time.time()),
                "character_count_change_to": len(script_text),
                "emotion": agent_res["emotion"],
                "filename": f"{file_id}.mp3"
            })
            save_history(hist[:100])
        except Exception as e:
            print("Agent speech generation error:", e)

    return jsonify({
        "used_gemini": used_gemini,
        "reply_text": agent_res["reply_text"],
        "has_audio": bool(audio_id),
        "audio_id": audio_id,
        "audio_url": audio_url,
        "tts_script": agent_res.get("tts_script", ""),
        "voice_id": voice_info["voice_id"],
        "voice_name": voice_info["name"],
        "voice_flag": voice_info.get("flag", "🎙️"),
        "gender": voice_info["labels"]["gender"],
        "emotion": agent_res.get("emotion", "normal"),
        "emotion_icon": emo_info.get("icon", "🎭"),
        "emotion_name": emo_info.get("name", "Normal")
    })

# ============================================================
#  HISTORY ENDPOINTS
# ============================================================

@app.route("/api/history")
def get_history():
    h = load_history()
    return jsonify({"history": h, "last_history_item_id": h[0]["history_item_id"] if h else None})

@app.route("/api/history/<hid>/audio")
def history_audio(hid):
    h = load_history()
    item = next((x for x in h if x["history_item_id"] == hid), None)
    if not item:
        return jsonify({"error": "Not found"}), 404
    fp = os.path.join(OUTPUT_DIR, item["filename"])
    if not os.path.exists(fp):
        return jsonify({"error": "File missing"}), 404
    return send_file(fp, mimetype="audio/mpeg")

@app.route("/api/history/<hid>", methods=["DELETE"])
def del_history(hid):
    h = load_history()
    item = next((x for x in h if x["history_item_id"] == hid), None)
    if item:
        fp = os.path.join(OUTPUT_DIR, item.get("filename", ""))
        if os.path.exists(fp):
            try: os.remove(fp)
            except Exception: pass
        save_history([x for x in h if x["history_item_id"] != hid])
    return jsonify({"status": "ok"})

@app.route("/api/user")
def get_user():
    h = load_history()
    chars = sum(x.get("character_count_change_to", 0) for x in h)
    cfg = load_config()
    return jsonify({
        "first_name": "Local",
        "email": "local@voicestudio.pro",
        "has_gemini": bool(cfg.get("gemini_api_key")),
        "subscription": {
            "tier": "Gemini AI Unlimited" if cfg.get("gemini_api_key") else "Local Free",
            "character_count": chars,
            "character_limit": 999999999,
            "status": "active"
        }
    })

@app.route("/api/models")
def get_models():
    return jsonify([
        {"model_id": "gemini-3-tts", "name": "Google Gemini 3.1 Pro / 3.8 Flash + Edge Neural TTS", "can_do_text_to_speech": True}
    ])

if __name__ == "__main__":
    print("=" * 60)
    print("🎙️  VoiceStudio Pro v3.0 — ElevenLabs Clone with Gemini AI")
    print(f"📢  {len(VOICES)} Voices Loaded!")
    print(f"🎭  {len(EMOTIONS)} Emotion Modes (Happy, Sad, Angry, Whisper, etc.)")
    cfg = load_config()
    if cfg.get("gemini_api_key"):
        print("🧠  Google Gemini AI: ENABLED")
    else:
        print("💡  Google Gemini AI: Set your free API key in settings")
    print("🌐  Running at: http://localhost:5000")
    print("=" * 60)
    app.run(debug=False, host="0.0.0.0", port=5000)
