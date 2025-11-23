# Drop2Print
Lightweight web app to print PDF files. Drag-and-drop frontend, FastAPI backend, Docker-ready.

## Features
- `/` – user panel with a large drag-and-drop area that uploads PDFs and sends them to print.
- `/admin` – admin panel (password protected) to set default copy count, view stats, and see recent jobs.
- Optional watch directory (e.g., mounted Samba share): drop PDFs into the folder and the app will pick them up, print, log status, and delete the original files.
- Backend stores jobs in SQLite, invokes printing (default `lp`/CUPS), and records job status.
- Configurable through environment variables (DB path, upload directory, printers, admin password, watch folder, etc.).

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
The service listens on port `8000`. By default, it mounts `app/uploads` and `app/db` from the host, so jobs and the database persist between restarts. Set `DROP2PRINT_PRINTER` via env (uncomment in `docker-compose.yml`) or at runtime if you need a specific printer.

### Watching a Samba share (or any folder)
1. Mount the Samba share on the host (e.g., `/mnt/printer_share`).
2. Add a volume to the compose file: `- /mnt/printer_share:/incoming`.
3. Set `DROP2PRINT_WATCH_PATH=/incoming` (and optionally `DROP2PRINT_WATCH_INTERVAL`).

Every PDF copied into the watched folder will be moved into the app, printed, logged, and the source file will be removed.

#### Example Samba mount on Linux
```bash
sudo apt-get install -y cifs-utils
sudo mkdir -p /mnt/printer_share
sudo mount -t cifs //SERVER/SHARE /mnt/printer_share \
  -o username=USER,password=PASS,vers=3.0,uid=$(id -u),gid=$(id -g)
```
Then update `docker-compose.yml`:
```yaml
    volumes:
      - ./app/uploads:/app/app/uploads
      - ./app/db:/app/app/db
      - /mnt/printer_share:/incoming
    environment:
      DROP2PRINT_WATCH_PATH: /incoming
```
Replace `SERVER`, `SHARE`, `USER`, `PASS` with your Samba server details. Use a systemd unit or `/etc/fstab` entry if you want the share to auto-mount on boot.

#### Docker-managed CIFS volume (no manual mount)
Docker can mount the share via a named volume:
```yaml
services:
  app:
    ...
    volumes:
      - ./app/uploads:/app/app/uploads
      - ./app/db:/app/app/db
      - samba-share:/incoming
    environment:
      DROP2PRINT_WATCH_PATH: /incoming

volumes:
  samba-share:
    driver: local
    driver_opts:
      type: cifs
      o: username=${SAMBA_USER},password=${SAMBA_PASS},vers=3.0
      device: //SERVER/SHARE
```
Supply `SAMBA_USER`, `SAMBA_PASS`, and optionally `SAMBA_DOMAIN`, `vers`, etc. via `.env` or your shell when running `docker compose up`. Docker will mount the share automatically each time the stack starts.

## Configuration
- `DROP2PRINT_DB_PATH` – path to the SQLite file (default `app/db/drop2print.sqlite3`).
- `DROP2PRINT_UPLOAD_PATH` – directory for uploaded files (default `app/uploads`).
- `DROP2PRINT_PRINTER` – printer name for `lp`; if empty, the default printer is used.
- `DROP2PRINT_ADMIN_PASSWORD` – password required to access `/admin` (default `changeme`; override in production).
- `DROP2PRINT_WATCH_PATH` – optional path watched for PDF files (drop PDFs here to auto-print).
- `DROP2PRINT_WATCH_INTERVAL` – polling interval in seconds for the watcher (default `5`).

After starting the app, visit `/admin/login` (or `/admin` to be redirected) and enter the configured password.
