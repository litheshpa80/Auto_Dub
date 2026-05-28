import asyncio
import tempfile
import os
from deep_translator import GoogleTranslator
import edge_tts

async def translate_text(text: str, target_lang: str) -> str:
    """Translate text using deep-translator."""
    if not text or not text.strip():
        return ""
    
    # Map our UI languages to Google Translate codes
    lang_map = {
        "spanish": "es",
        "french": "fr",
        "german": "de",
        "italian": "it",
        "portuguese": "pt",
        "hindi": "hi",
        "english": "en",
        "japanese": "ja",
        "korean": "ko",
        "chinese": "zh-CN",
        "russian": "ru"
    }
    target_code = lang_map.get(target_lang.lower(), "en")
    
    try:
        translated = GoogleTranslator(source='auto', target=target_code).translate(text)
        return translated
    except Exception as e:
        print(f"Translation error: {e}")
        return text

async def text_to_speech(text: str, target_lang: str) -> str:
    """Generate TTS using edge-tts and return the path to the temporary audio file."""
    if not text or not any(c.isalnum() for c in text):
        return None
        
    # Map languages to edge-tts voices
    voice_map = {
        "spanish": "es-ES-AlvaroNeural",
        "french": "fr-FR-HenriNeural",
        "german": "de-DE-KillianNeural",
        "italian": "it-IT-DiegoNeural",
        "portuguese": "pt-PT-DuarteNeural",
        "hindi": "hi-IN-MadhurNeural",
        "english": "en-US-ChristopherNeural",
        "japanese": "ja-JP-KeitaNeural",
        "korean": "ko-KR-InJoonNeural",
        "chinese": "zh-CN-YunxiNeural",
        "russian": "ru-RU-DmitryNeural"
    }
    
    voice = voice_map.get(target_lang.lower(), "en-US-ChristopherNeural")
    
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return output_path
    except Exception as e:
        print(f"TTS error: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return None
