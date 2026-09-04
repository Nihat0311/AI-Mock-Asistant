import os
import whisper

model = None
try:
    # Model lokalda cache-də saxlanılır və pulsuz çalışır
    model = whisper.load_model("base")
    print("✅ Whisper (base) modeli lokalda hazırdır.")
except Exception as e:
    print(f"❌ Whisper modeli yüklənərkən xəta: {e}")

def transcribe_audio(audio_file_path: str) -> str:
    """
    Səs faylını (mp3, wav və s.) qəbul edir və mətnə çevirir.
    """
    if not model:
        return "Xəta: Whisper modeli yüklənməyib."

    try:
        if not os.path.exists(audio_file_path):
            return "Xəta: Səs faylı tapılmadı."
            
        result = model.transcribe(audio_file_path)
        return result["text"].strip()
    except Exception as e:
        print(f"❌ STT Xətası (Whisper): {e}")
        return ""