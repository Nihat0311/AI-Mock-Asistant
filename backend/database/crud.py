import hashlib
from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from . import models, schemas


def generate_content_hash(title: str, description: str) -> str:
    """
    Başlıq və mətnin boşluqlarını silib kiçik hərfə çevirir və unikallıq üçün SHA-256 həşini yaradır.
    """
    clean_text = f"{title.strip().lower()}:{description.strip().lower()}"
    return hashlib.sha256(clean_text.encode('utf-8')).hexdigest()


def get_job_description(db: Session, job_id: int):
    return db.query(models.JobDescription).filter(models.JobDescription.id == job_id).first()


def get_job_by_hash(db: Session, content_hash: str):
    return db.query(models.JobDescription).filter(models.JobDescription.content_hash == content_hash).first()


def get_job_descriptions(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    is_custom: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = "date",
    order: str = "desc"
):
    """
    Gələcək Frontend interfeysi üçün vakansiyaları filtrləyir, axtarır və sıralayır.
    """
    query = db.query(models.JobDescription)

    # 1. Filtrləmə: Yalnız custom və ya hazır elanlar
    if is_custom is not None:
        query = query.filter(models.JobDescription.is_custom == is_custom)

    # 2. Case-Insensitive (registrdən asılı olmayan) axtarış
    if search and search.strip():
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.JobDescription.title.ilike(search_fmt),
                models.JobDescription.description.ilike(search_fmt),
                models.JobDescription.extracted_skills.ilike(search_fmt)
            )
        )

    # 3. Sıralama sahələrinin xəritələnməsi ('date' sahəsini created_at ilə bağlayırıq)
    sort_map = {
        "date": models.JobDescription.created_at,
        "created_at": models.JobDescription.created_at,
        "id": models.JobDescription.id,
        "title": models.JobDescription.title
    }
    sort_column = sort_map.get(sort_by, models.JobDescription.created_at)

    if order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # 4. Səhifələmə (Pagination)
    return query.offset(skip).limit(limit).all()


def create_or_get_job_description(
    db: Session,
    job: schemas.JobDescriptionCreate,
    extracted_skills: str = None,
    is_custom: bool = True
):
    """
    Əgər elan bazada varsa mövcud olanı qaytarır, yoxdursa bazaya yenisini yazır.
    """
    c_hash = generate_content_hash(job.title, job.description)

    # 1. HASH vasitəsilə təkrarı yoxlayırıq
    existing_job = get_job_by_hash(db, c_hash)
    if existing_job:
        return existing_job, False  # (elan, yeni_yaradildi=False)

    # 2. Təkrar deyilsə bazaya əlavə edirik
    db_job = models.JobDescription(
        title=job.title,
        level=job.level,
        description=job.description,
        extracted_skills=extracted_skills,
        content_hash=c_hash,
        is_custom=is_custom
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job, True  # (elan, yeni_yaradildi=True)


def delete_job_description(db: Session, job_id: int) -> bool:
    """İş elanını ID-yə görə bazadan silir"""
    db_job = get_job_description(db, job_id)
    if db_job:
        db.delete(db_job)
        db.commit()
        return True
    return False