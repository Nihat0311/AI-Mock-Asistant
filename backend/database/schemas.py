from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


# ── Job Description Sxemləri ───────────────────────────────────────

class JobDescriptionBase(BaseModel):
    title: str
    level: str
    description: str


class JobDescriptionCreate(JobDescriptionBase):
    pass


class JobDescriptionResponse(JobDescriptionBase):
    id: int
    extracted_skills: Optional[str] = None
    is_custom: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Müsahibə (Interview) Sxemləri ──────────────────────────────────

class StartInterviewRequest(BaseModel):
    job_id: Optional[int] = None                          # Rejim 1: Hazır elan seçilərsə
    custom_job: Optional[JobDescriptionCreate] = None     # Rejim 2: Yeni elan daxil edilərsə


class InterviewStartResponse(BaseModel):
    status: str
    session_id: int
    job_id: int
    job_title: str
    ai_question: str
    ai_audio_file: str


class InterviewReplyResponse(BaseModel):
    status: str
    user_answer: str
    ai_question: str
    ai_audio_file: str


class InterviewEvaluationResponse(BaseModel):
    status: str
    session_id: int
    score: int
    strengths: List[str]
    weaknesses: List[str]
    focus_areas: List[str]
    overall_summary: str