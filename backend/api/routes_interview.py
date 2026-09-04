import os
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.database import crud, models, schemas
from backend.database.database import get_db
from backend.services.llm_service import generate_next_question, evaluate_interview
from backend.services.whisper_service import transcribe_audio
from backend.services.elevenlabs_service import generate_audio_from_text

router = APIRouter(
    prefix="/interview",
    tags=["Interview Flow"]
)

chat_histories = {}

ALLOWED_AUDIO_TYPES = [
    "audio/wav", "audio/x-wav", "audio/mp3", "audio/mpeg", 
    "audio/m4a", "audio/x-m4a", "audio/mp4", "audio/aac", 
    "audio/ogg", "audio/opus", "application/ogg", "video/mp4"
]

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".mp4"}


@router.get("/sessions")
async def get_all_sessions(db: Session = Depends(get_db)):
    """
    Bazada olan bütün müsahibə sessiyalarını və onların RAM-da aktiv olub-olmadığını siyahılayır.
    """
    sessions = db.query(models.InterviewSession).all()
    result = []
    for s in sessions:
        job = crud.get_job_description(db, job_id=s.job_id) if s.job_id else None
        result.append({
            "session_id": s.id,
            "job_id": s.job_id,
            "job_title": job.title if job else "Bilinmir",
            "is_active_in_ram": s.id in chat_histories,
            "messages_in_ram": len(chat_histories[s.id]) if s.id in chat_histories else 0
        })
    return result


@router.post("/start", response_model=schemas.InterviewStartResponse)
async def start_interview(
    request: schemas.StartInterviewRequest,
    db: Session = Depends(get_db)
):
    """
    İki rejimdə müsahibə başladır:
    1. Bazada olan job_id daxil edilərsə -> Hazır elan üzrə başladır.
    2. custom_job daxil edilərsə -> HASH ilə təkrarı yoxlayır, bazaya yazır və başladır.
    """
    job = None

    if request.job_id:
        job = crud.get_job_description(db, job_id=request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Göstərilən ID ilə iş elanı tapılmadı.")

    elif request.custom_job:
        job, is_new = crud.create_or_get_job_description(
            db=db, 
            job=request.custom_job, 
            extracted_skills=f"{request.custom_job.title}, {request.custom_job.level}",
            is_custom=True
        )

    else:
        raise HTTPException(
            status_code=400, 
            detail="Müsahibəni başlatmaq üçün ya 'job_id', ya da 'custom_job' göndərilməlidir."
        )

    db_session = models.InterviewSession(job_id=job.id)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    session_id = db_session.id
    chat_histories[session_id] = []

    job_skills = job.extracted_skills or job.title
    first_question = generate_next_question(chat_histories[session_id], job_skills)

    chat_histories[session_id].append({"role": "model", "parts": [first_question]})

    ai_audio_path = f"ai_reply_{session_id}.mp3"
    generate_audio_from_text(text=first_question, output_path=ai_audio_path)

    return {
        "status": "success",
        "session_id": session_id,
        "job_id": job.id,
        "job_title": job.title,
        "ai_question": first_question,
        "ai_audio_file": ai_audio_path
    }


@router.post("/reply", response_model=schemas.InterviewReplyResponse)
async def reply_to_ai(
    session_id: int = Form(...),
    text_answer: Optional[str] = Form(None),
    audio_answer: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Namizədin cavabını (mətn və ya səs) qəbul edir və dinamik şəkildə adaptiv növbəti sualı qaytarır.
    """
    # 1. Sessiyanın yoxlanılması (Server yenidən başladıqda qoruma)
    if session_id not in chat_histories:
        db_session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
        if not db_session:
            raise HTTPException(
                status_code=404, 
                detail="Sessiya tapılmadı. Zəhmət olmasa /interview/start ilə yeni müsahibə başladın."
            )
        chat_histories[session_id] = []

    user_text = text_answer

    # 2. Səs faylının varlığının təhlükəsiz yoxlanılması
    has_audio = audio_answer and audio_answer.filename and audio_answer.filename.strip() != ""
    
    if has_audio:
        file_ext = os.path.splitext(audio_answer.filename)[1].lower()
        
        is_valid_type = (
            audio_answer.content_type in ALLOWED_AUDIO_TYPES 
            or file_ext in ALLOWED_EXTENSIONS
        )
        
        if not is_valid_type:
            raise HTTPException(
                status_code=400,
                detail=f"Dəstəklənməyən səs formatı ({audio_answer.filename}). Yalnız .m4a, .mp3, .wav, .ogg və .opus yükləyin."
            )

        temp_path = f"temp_user_{session_id}{file_ext if file_ext else '.ogg'}"
        
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(audio_answer.file, buffer)
            
            if os.path.getsize(temp_path) > 0:
                transcribed_text = transcribe_audio(temp_path)
                
                if transcribed_text and transcribed_text.strip():
                    user_text = transcribed_text.strip()
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Səs faylı oxuna bilmədi və ya səsdə nitq aşkar edilmədi."
                    )
            else:
                user_text = text_answer

        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=500,
                detail=f"Səs tanıma xətası baş verdi: {str(e)}"
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # 3. Cavab mətninin yoxlanılması
    if not user_text or user_text.strip() == "":
        raise HTTPException(
            status_code=400, 
            detail="Zəhmət olmasa, cavabınızı mətn və ya səs olaraq təqdim edin."
        )

    # 4. Dialoq tarixçəsinə istifadəçi cavabının əlavə edilməsi
    chat_histories[session_id].append({"role": "user", "parts": [user_text.strip()]})

    # 5. Bazadan vakansiya bacarıqlarının job_id vasitəsilə təhlükəsiz çəkilməsi
    db_session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
    job_skills = "IT Development, Problem Solving"
    if db_session and db_session.job_id:
        job = crud.get_job_description(db, job_id=db_session.job_id)
        if job:
            job_skills = job.extracted_skills or job.title

    # 6. Gemini AI vasitəsilə növbəti adaptiv sualın yaradılması
    ai_reply_text = generate_next_question(chat_histories[session_id], job_skills)

    chat_histories[session_id].append({"role": "model", "parts": [ai_reply_text]})

    # 7. Sualın səsə çevrilməsi
    ai_audio_path = f"ai_reply_{session_id}.mp3"
    generate_audio_from_text(text=ai_reply_text, output_path=ai_audio_path)

    return {
        "status": "success",
        "user_answer": user_text.strip(),
        "ai_question": ai_reply_text,
        "ai_audio_file": ai_audio_path
    }


@router.post("/finish", response_model=schemas.InterviewEvaluationResponse)
async def finish_interview(
    session_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Müsahibəni yekunlaşdırır, istifadəçinin bütün tarixçəsini analiz edir
    və 100 üzərindən ədalətli bal, güclü/zəif tərəflər və fokuslanmalı olduğu sahələri qaytarır.
    """
    if session_id not in chat_histories or not chat_histories[session_id]:
        raise HTTPException(
            status_code=400, 
            detail="Sessiya tapılmadı və ya aktiv müsahibə yoxdur. Zəhmət olmasa yeni müsahibə başladın."
        )

    db_session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
    job_skills = "IT Development, Problem Solving"
    if db_session and db_session.job_id:
        job = crud.get_job_description(db, job_id=db_session.job_id)
        if job:
            job_skills = job.extracted_skills or job.title

    try:
        report = evaluate_interview(chat_histories[session_id], job_skills)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Qiymətləndirmə zamanı xəta baş verdi. Zəhmət olmasa yenidən cəhd edin: {str(e)}"
        )

    return {
        "status": "completed",
        "session_id": session_id,
        "score": report.get("score", 0),
        "strengths": report.get("strengths", []),
        "weaknesses": report.get("weaknesses", []),
        "focus_areas": report.get("focus_areas", []),
        "overall_summary": report.get("overall_summary", "")
    }