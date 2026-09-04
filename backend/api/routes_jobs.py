from enum import Enum
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import crud, schemas
from backend.database.database import get_db


# Swagger UI üçün dropdown seçimləri
class SortByEnum(str, Enum):
    date = "date"
    id = "id"
    title = "title"


class OrderEnum(str, Enum):
    asc = "asc"
    desc = "desc"


router = APIRouter(
    prefix="/jobs",
    tags=["Job Descriptions"]
)


@router.post("/", response_model=schemas.JobDescriptionResponse)
def create_job(job: schemas.JobDescriptionCreate, db: Session = Depends(get_db)):
    """
    Yeni iş elanı əlavə edir. HASH vasitəsilə eyni elanın bazada olub-olmadığını yoxlayır.
    """
    db_job, is_new = crud.create_or_get_job_description(db=db, job=job, is_custom=False)
    return db_job


@router.get("/", response_model=List[schemas.JobDescriptionResponse])
def read_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_custom: Optional[bool] = Query(None, description="True (istifadəçi elanları), False (sistem elanları)"),
    search: Optional[str] = Query(None, description="Başlıq, mətn və bacarıqlarda registrdən asılı olmayan axtarış"),
    sort_by: SortByEnum = Query(SortByEnum.date, description="Sıralama sahəsi ('date', 'id', 'title')"),
    order: OrderEnum = Query(OrderEnum.desc, description="'desc' (ən yenilər yuxarıda) və ya 'asc'"),
    db: Session = Depends(get_db)
):
    """
    Gələcək Frontend vizualizasiyası üçün vakansiya siyahısı API-ı:
    - **is_custom**: True (istifadəçi elanları), False (sistem elanları)
    - **search**: Başlıq və mətndə axtarış sözü (registrdən asılı deyil)
    - **sort_by**: Sıralama sahəsi ('date', 'id', 'title')
    - **order**: 'desc' (ən yenilər yuxarıda) və ya 'asc'
    """
    return crud.get_job_descriptions(
        db=db,
        skip=skip,
        limit=limit,
        is_custom=is_custom,
        search=search,
        sort_by=sort_by.value,
        order=order.value
    )


@router.get("/{job_id}", response_model=schemas.JobDescriptionResponse)
def read_job(job_id: int, db: Session = Depends(get_db)):
    """Spesifik bir iş elanını ID-yə görə gətirir"""
    db_job = crud.get_job_description(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="İş elanı tapılmadı")
    return db_job


@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Spesifik bir iş elanını bazadan silir"""
    success = crud.delete_job_description(db, job_id=job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Silinmədi: İş elanı tapılmadı")
    return {"status": "success", "message": f"ID-si {job_id} olan iş elanı silindi"}