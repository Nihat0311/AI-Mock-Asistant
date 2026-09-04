from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)            # Məs: Backend Developer
    level = Column(String)                        # Məs: Junior, Middle, Senior
    description = Column(Text)                    # İşin tam mətni
    extracted_skills = Column(Text, nullable=True) # Analizdən sonra tapılan bacarıqlar
    content_hash = Column(String, unique=True, index=True, nullable=True) # Təkrar elanları tutmaq üçün
    is_custom = Column(Boolean, default=False)     # True = İstifadəçi əlavə edib, False = Hazır baza
    created_at = Column(DateTime, default=datetime.utcnow)

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id"))
    relevance_score = Column(Float, nullable=True)
    feedback_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("JobDescription")

class HRQuestion(Base):
    __tablename__ = "hr_questions"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, index=True)
    ideal_answer = Column(Text)