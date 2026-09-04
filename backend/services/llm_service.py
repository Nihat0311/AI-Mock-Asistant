import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types as gemini_types
from backend.core.prompts import SYSTEM_PROMPT, get_jd_analysis_prompt

load_dotenv()

# ── Pulsuz Gemini Konfiqurasiyası ────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.6-flash"

gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"✅ Gemini client hazırdır (model: {GEMINI_MODEL})")
    except Exception as e:
        print(f"⚠️ Gemini müştərisi yaradılarkən xəta: {e}")
else:
    print("❌ GEMINI_API_KEY tapılmadı! .env faylını yoxlayın.")


# ══════════════════════════════════════════════════════════════════
#  Gemini Helper Funksiyaları
# ══════════════════════════════════════════════════════════════════

def _gemini_generate(system_prompt: str, user_prompt: str) -> str:
    """Tək turluq mətn generasiyası (JD analizi üçün)."""
    if not gemini_client:
        raise RuntimeError("Gemini client aktiv deyil.")

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=gemini_types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=1024,
        ),
    )
    return response.text.strip()


def _gemini_chat(system_prompt: str, chat_history: list, user_prompt: str) -> str:
    """Çox turluq müsahibə dialoqu."""
    if not gemini_client:
        raise RuntimeError("Gemini client aktiv deyil.")

    formatted_history = []
    for msg in chat_history:
        role = msg.get("role", "user")
        parts_data = msg.get("parts", [])
        formatted_history.append(
            gemini_types.Content(
                role=role,
                parts=[gemini_types.Part.from_text(text=p) for p in parts_data],
            )
        )

    chat = gemini_client.chats.create(
        model=GEMINI_MODEL,
        config=gemini_types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=1024,
        ),
        history=formatted_history,
    )
    response = chat.send_message(user_prompt)
    return response.text.strip()


# ══════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════

def analyze_job_description(job_title: str, description: str) -> str:
    """Job Description-u analiz edib əsas bacarıqları çıxarır."""
    prompt = get_jd_analysis_prompt(job_title, description)

    try:
        return _gemini_generate(SYSTEM_PROMPT, prompt)
    except Exception as e:
        print(f"Gemini JD analiz xətası: {e}")
        return "İş elanı təhlil edilərkən xəta baş verdi."


def generate_next_question(chat_history: list, job_skills: str) -> str:
    """
    Tarixçəyə və bacarıqlara əsasən adaptiv növbəti sualı yaradır:
    - Cavab doğrudursa -> Çətinliyi artırır.
    - Cavab yanlışdırsa -> Sualı asanlaşdırır.
    """
    last_user_message = "Müsahibəyə başlayaq."
    if chat_history and chat_history[-1].get("parts"):
        last_user_message = chat_history[-1]["parts"][0]

    prompt = f"""
    Tələb olunan əsas bacarıqlar: {job_skills}.
    
    ADAPTİV MÜSAHİBƏ QAYDALARI:
    1. Namizədin veridiyi son cavabı: '{last_user_message}' dəyərləndir.
    2. Cavab DOĞRUDURSA və ya DƏRİNDİRSƏ: Namizədi qısaca təqdir et və növbəti sualı daha ÇƏTİN / dərin konseptlərdən ver.
    3. Cavab YANLIŞDIRSA və ya əskikdirsə: Qısaca doğrusunu izah et və növbəti sualı daha ASAN / bünövrə mövzudan ver.
    4. Yalnız 1 aydın sual ver. Qısa və dəqiq ol.
    """

    history_to_pass = chat_history[:-1] if len(chat_history) > 1 else []

    try:
        return _gemini_chat(SYSTEM_PROMPT, history_to_pass, prompt)
    except Exception as e:
        print(f"Gemini sual generasiyası xətası: {e}")
        return "Növbəti sual hazırlanarkən xəta baş verdi."


def evaluate_interview(chat_history: list, job_skills: str) -> dict:
    """
    Bütün müsahibə tarixçəsini analiz edir və JSON formatında 100 üzərindən bal və hesabat qaytarır.
    """
    if not gemini_client:
        raise RuntimeError("Gemini client aktiv deyil.")

    formatted_history = ""
    for msg in chat_history:
        role = "Müsahibəçi (AI)" if msg.get("role") == "model" else "Namizəd"
        parts = msg.get("parts", [])
        text = parts[0] if parts else ""
        formatted_history += f"{role}: {text}\n"

    eval_prompt = f"""
    Sən peşəkar İT texniki qiymətləndirmə ekspertisən.
    Vakansiya tələbləri: {job_skills}

    Aşağıdakı müsahibə tarixçəsini diqqətlə analiz et və namizəd üçün 100 üzərindən bal və yekun hesabat hazırla.

    MÜSAHİBƏ TARİXÇƏSİ:
    {formatted_history}

    CAVAB FORMATI (Yalnız təmiz JSON qaytar):
    {{
        "score": 0-100 arası tam rəqəm,
        "strengths": ["Güclü tərəf 1", "Güclü tərəf 2"],
        "weaknesses": ["Zəif tərəf 1", "Zəif tərəf 2"],
        "focus_areas": ["Əsas fokuslanmalı olduğu mövzu 1", "Mövzu 2"],
        "overall_summary": "Namizədin ümumi performansı haqqında 2-3 cümləlik yekun rəy."
    }}
    """

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=eval_prompt,
            config=gemini_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        return json.loads(raw_text)

    except Exception as e:
        print(f"❌ Gemini qiymətləndirmə xətası: {e}")
        raise RuntimeError(f"Qiymətləndirmə hesabatı hazırlanarkən xəta baş verdi: {str(e)}")