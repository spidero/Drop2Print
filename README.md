# Drop2Print
Lightweight web app to print PDF files. Drag-and-drop frontend, FastAPI backend, Docker-ready.

## Features
- `/` – user panel with a large drag-and-drop area that uploads PDFs and sends them to print.
- `/admin` – admin panel to set default copy count, view stats, and see recent jobs.
- Backend stores jobs in SQLite, invokes printing (default `lp`/CUPS), and records job status.
- Configurable through environment variables (DB path, upload directory, default printer).

## Local run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open `http://localhost:8000` (user panel) or `http://localhost:8000/admin`.

## Docker
```bash
docker build -t drop2print .
docker run -p 8000:8000 -v $(pwd)/app/uploads:/app/app/uploads drop2print
```
> Note: the image does not install the CUPS client by default. Add `apt-get update && apt-get install -y cups-client` in the Dockerfile if you need printing from inside the container.
> We use FastAPI/Pydantic v1 (compatible with SQLModel). After changing Python versions, reinstall dependencies (`pip install -r requirements.txt`).

## Docker Compose
```bash
docker compose up --build
```
The service listens on port `8000`. By default, it mounts `app/uploads` and `app/db` from the host, so jobs and the database persist between restarts. Set `DROP2PRINT_PRINTER` in `docker-compose.yml` or at runtime if you need a specific printer.

## Configuration
- `DROP2PRINT_DB_PATH` – path to the SQLite file (default `app/db/drop2print.sqlite3`).
- `DROP2PRINT_UPLOAD_PATH` – directory for uploaded files (default `app/uploads`).
- `DROP2PRINT_PRINTER` – printer name for `lp`; if empty, the default printer is used.
