import os
import asyncio
import concurrent.futures
import edge_tts
from langdetect import detect

# Proyektin ana qovluğunu təyin edirik (AI_Mock_Asis)
SERVICES_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SERVICES_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

async def _create_audio_async(text: str, output_path: str):
    try:
        try:
            detected_lang = detect(text)
        except Exception:
            detected_lang = "az"

        if detected_lang == "en":
            voice = "en-US-JennyNeural"
        elif detected_lang == "az":
            voice = "az-AZ-BanuNeural"
        else:
            voice = "az-AZ-BanuNeural" if any(char in text.lower() for char in "əğıöşü") else "en-US-JennyNeural"

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"Async TTS Xətası: {e}")
        return False

def generate_audio_from_text(text: str, output_path: str = "ai_question.mp3"):
    """
    FastAPI dövrəsi ilə toqquşmadan səs faylını mütləq ünvanla PROJECT_ROOT qovluğuna yazır.
    """
    if not os.path.isabs(output_path):
        output_path = os.path.join(PROJECT_ROOT, output_path)

    try:
        # FastAPI-nin event loop-u ilə toqquşmamaq üçün ayrı resursda işlədirik
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(_create_audio_async(text, output_path)))
            success = future.result()

        if success and os.path.exists(output_path):
            print(f"✅ Səs faylı uğurla yaradıldı: {output_path}")
            return output_path
        else:
            print("❌ Səs faylı yaradıla bilmədi.")
            return None
    except Exception as e:
        print(f"❌ TTS Xətası (Edge-TTS): {e}")
        return None