import json
import logging
import os
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlmodel import Session, select

from app.db import get_session, init_db, create_session
from app.i18n import TRANSLATIONS, get_lang
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
ADMIN_PASSWORD = os.getenv("DROP2PRINT_ADMIN_PASSWORD")
WATCH_PATH = os.getenv("DROP2PRINT_WATCH_PATH")
WATCH_INTERVAL = int(os.getenv("DROP2PRINT_WATCH_INTERVAL", "5"))


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    start_watch_service()


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


def run_print_job(job: PrintJob, session: Session) -> None:
    logger.info(
        "Printing job %s (%s) with %s copies from %s",
        job.id,
        job.filename,
        job.copies,
        job.storage_path,
    )
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

    if job.status == PrintStatus.failed:
        logger.error("Job %s failed: %s", job.id, job.error)
    else:
        logger.info("Job %s finished with status %s", job.id, job.status)


watcher_started = False
watcher_lock = threading.Lock()


def start_watch_service() -> None:
    global watcher_started  # pylint: disable=global-statement
    if not WATCH_PATH:
        logger.info("File watcher disabled (DROP2PRINT_WATCH_PATH not set).")
        return

    with watcher_lock:
        if watcher_started:
            return

        watch_dir = Path(WATCH_PATH)
        watch_dir.mkdir(parents=True, exist_ok=True)
        thread = threading.Thread(target=watch_directory_loop, args=(watch_dir,), name="drop2print-watcher", daemon=True)
        thread.start()
        watcher_started = True
        logger.info("Started file watcher for %s (interval %ss)", watch_dir, WATCH_INTERVAL)


def watch_directory_loop(watch_dir: Path) -> None:
    poll_interval = max(1, WATCH_INTERVAL)
    while True:
        try:
            for file_path in sorted(watch_dir.iterdir()):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() != ".pdf":
                    continue
                process_watched_file(file_path)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Watcher encountered an error while scanning %s", watch_dir)
        time.sleep(poll_interval)


def process_watched_file(file_path: Path) -> None:
    logger.info("Detected PDF from watch dir: %s", file_path)
    session = create_session()
    try:
        copies = int(get_setting(session, "copies", str(Setting.default_copies())).value)
        dest_name = f"{uuid.uuid4()}_{file_path.name}"
        dest_path = UPLOAD_DIR / dest_name

        try:
            shutil.copy2(file_path, dest_path)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to copy watched file %s", file_path)
            return

        try:
            file_path.unlink()
        except OSError as exc:
            logger.warning("Unable to delete source file %s after copying: %s", file_path, exc)

        job = PrintJob(
            filename=file_path.name,
            storage_path=str(dest_path),
            copies=copies,
            status=PrintStatus.pending,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        run_print_job(job, session)
    finally:
        session.close()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    lang = get_lang(request)
    t = TRANSLATIONS[lang]
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "t": t,
            "lang": lang,
            "translations_json": json.dumps(t),
            "watch_path": WATCH_PATH,
            "printer_name": printer_service.printer_name,
        },
    )
    response.set_cookie("lang", lang)
    return response


@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, session: Session = Depends(get_session)):
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=500, detail="Admin password not configured.")
    if request.cookies.get("admin_auth") != ADMIN_PASSWORD:
        return RedirectResponse(url=f"/admin/login?lang={get_lang(request)}", status_code=302)
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

    run_print_job(job, session)

    return JSONResponse(content=serialize_job(job))
@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_form(request: Request):
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=500, detail="Admin password not configured.")
    lang = get_lang(request)
    t = TRANSLATIONS[lang]
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "t": t, "lang": lang, "translations_json": json.dumps(t)},
    )


@app.post("/admin/login")
def admin_login(request: Request, password: str = Form(...)):
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=500, detail="Admin password not configured.")
    lang = get_lang(request)
    t = TRANSLATIONS[lang]
    if password != ADMIN_PASSWORD:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "t": t,
                "lang": lang,
                "translations_json": json.dumps(t),
                "error": t.get("login_error", "Invalid password"),
            },
            status_code=401,
        )
    response = RedirectResponse(url="/admin", status_code=302)
    response.set_cookie("admin_auth", ADMIN_PASSWORD, httponly=True, samesite="lax")
    response.set_cookie("lang", lang)
    return response
