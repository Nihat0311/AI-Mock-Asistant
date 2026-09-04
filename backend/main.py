import mimetypes
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Router importları
from backend.api.routes_interview import router as interview_router
from backend.api.routes_jobs import router as jobs_router  # 1. BU SƏTİRİ ƏLAVƏ EDİN

app = FastAPI(title="Dory AI - Interview Assistant Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router-lərin qoşulması
app.include_router(interview_router)
app.include_router(jobs_router)  # 2. BU SƏTİRİ ƏLAVƏ EDİN

AUDIO_DIR = "audio_files"
for directory in ["static", AUDIO_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = filename
    if not os.path.exists(file_path):
        file_path = os.path.join(AUDIO_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Səs faylı tapılmadı")

    media_type, _ = mimetypes.guess_type(file_path)
    if not media_type:
        media_type = (
            "audio/webm" if filename.endswith(".webm") else "audio/mpeg"
        )

    return FileResponse(file_path, media_type=media_type)


@app.get("/")
async def read_index():
    index_path = os.path.join("static", "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(
            status_code=404, detail="static/index.html faylı tapılmadı"
        )
    return FileResponse(index_path)