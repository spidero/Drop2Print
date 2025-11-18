import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlmodel import Session, select

from app.db import get_session, init_db
from app.models import PrintJob, PrintStatus, Setting
from app.services.printer import PrinterService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("drop2print")

UPLOAD_DIR = Path(os.getenv("DROP2PRINT_UPLOAD_PATH", "app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Drop2Print", version="0.1.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
printer_service = PrinterService(printer_name=os.getenv("DROP2PRINT_PRINTER"))

TRANSLATIONS = {
    "en": {
        "title": "Drop2Print",
        "nav_user": "User panel",
        "nav_admin": "Admin",
        "drop_title": "Drop PDF files here",
        "drop_sub": "Files will be uploaded and sent to print automatically.",
        "drop_hint": "Drop PDF files here or click to choose.",
        "recent_jobs": "Recent jobs",
        "uploading": "Uploading {filename}...",
        "status": "Job #{id} ({filename}) status: {status}",
        "jobs_empty": "No jobs.",
        "loading": "Loading...",
        "settings": "Settings",
        "copies_label": "Number of copies per job",
        "save": "Save",
        "save_success": "Saved.",
        "save_error": "Save error",
        "stats": "Statistics",
        "total_jobs": "Total jobs",
        "printed": "Printed",
    },
    "pl": {
        "title": "Drop2Print",
        "nav_user": "Panel użytkownika",
        "nav_admin": "Administracja",
        "drop_title": "Przeciągnij pliki PDF",
        "drop_sub": "Pliki zostaną automatycznie wysłane do druku.",
        "drop_hint": "Upuść pliki PDF tutaj lub kliknij, aby wybrać.",
        "recent_jobs": "Ostatnie zadania",
        "uploading": "Wysyłanie {filename}...",
        "status": "Zadanie #{id} ({filename}) status: {status}",
        "jobs_empty": "Brak zadań.",
        "loading": "Ładowanie...",
        "settings": "Ustawienia",
        "copies_label": "Liczba kopii na zadanie",
        "save": "Zapisz",
        "save_success": "Zapisano.",
        "save_error": "Błąd zapisu",
        "stats": "Statystyki",
        "total_jobs": "Zadań łącznie",
        "printed": "Wydrukowane",
    },
}


def get_lang(request: Request) -> str:
    lang = request.query_params.get("lang") or request.cookies.get("lang") or "en"
    return lang if lang in TRANSLATIONS else "en"


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def get_setting(session: Session, key: str, default: str) -> Setting:
    result = session.exec(select(Setting).where(Setting.key == key)).first()
    if result:
        return result

    setting = Setting(key=key, value=default)
    session.add(setting)
    session.commit()
    session.refresh(setting)
    return setting


def set_setting(session: Session, key: str, value: str) -> Setting:
    setting = session.exec(select(Setting).where(Setting.key == key)).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        session.add(setting)
    session.commit()
    session.refresh(setting)
    return setting


def serialize_job(job: PrintJob) -> dict:
    return {
        "id": job.id,
        "filename": job.filename,
        "copies": job.copies,
        "status": job.status.value if job.status else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "printed_at": job.printed_at.isoformat() if job.printed_at else None,
        "error": job.error,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    lang = get_lang(request)
    t = TRANSLATIONS[lang]
    response = templates.TemplateResponse(
        "index.html",
        {"request": request, "t": t, "lang": lang, "translations_json": json.dumps(t)},
    )
    response.set_cookie("lang", lang)
    return response


@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, session: Session = Depends(get_session)):
    lang = get_lang(request)
    t = TRANSLATIONS[lang]
    copies = int(get_setting(session, "copies", str(Setting.default_copies())).value)
    recent_jobs: List[PrintJob] = session.exec(
        select(PrintJob).order_by(PrintJob.created_at.desc()).limit(10)
    ).all()
    total_jobs = session.exec(select(func.count()).select_from(PrintJob)).one()
    printed_jobs = session.exec(
        select(func.count()).select_from(PrintJob).where(PrintJob.status == PrintStatus.printed)
    ).one()
    stats = {"total_jobs": total_jobs, "printed": printed_jobs}
    response = templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "copies": copies,
            "recent_jobs": recent_jobs,
            "stats": stats,
            "t": t,
            "lang": lang,
            "translations_json": json.dumps(t),
        },
    )
    response.set_cookie("lang", lang)
    return response


@app.get("/api/settings")
def api_get_settings(session: Session = Depends(get_session)):
    copies = int(get_setting(session, "copies", str(Setting.default_copies())).value)
    return {"copies": copies}


@app.post("/api/settings")
def api_update_settings(copies: int = Form(..., ge=1), session: Session = Depends(get_session)):
    set_setting(session, "copies", str(copies))
    return {"copies": copies}


@app.get("/api/jobs")
def api_list_jobs(limit: int = 25, session: Session = Depends(get_session)):
    jobs = session.exec(select(PrintJob).order_by(PrintJob.created_at.desc()).limit(limit)).all()
    return [serialize_job(job) for job in jobs]


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...), session: Session = Depends(get_session)):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    copies = int(get_setting(session, "copies", str(Setting.default_copies())).value)
    save_name = f"{uuid.uuid4()}_{file.filename}"
    storage_path = UPLOAD_DIR / save_name

    with storage_path.open("wb") as buffer:
        data = await file.read()
        buffer.write(data)

    job = PrintJob(filename=file.filename, storage_path=str(storage_path), copies=copies, status=PrintStatus.pending)
    session.add(job)
    session.commit()
    session.refresh(job)

    try:
        printer_service.print_file(job)
        job.status = PrintStatus.printed
        job.printed_at = datetime.utcnow()
        job.error = None
    except Exception as exc:  # pylint: disable=broad-except
        job.status = PrintStatus.failed
        job.error = str(exc)
        logger.exception("Failed to print job %s", job.id)

    session.add(job)
    session.commit()
    session.refresh(job)

    return JSONResponse(content=serialize_job(job))
