# Drop2Print
Lekka aplikacja webowa do drukowania plików PDF. Frontend z drag & drop, backend w FastAPI, całość gotowa do uruchomienia w Dockerze.

## Funkcje
- `/` – panel użytkownika z obszarem drag & drop, automatyczne wysyłanie PDF do druku.
- `/admin` – panel administratora: liczba kopii, statystyki i szybki podgląd ostatnich zadań.
- Backend zapisuje zadania w SQLite, uruchamia druk (domyślnie `lp`/CUPS) i loguje statusy.
- Prosta konfiguracja przez zmienne środowiskowe (ścieżka bazy, katalog uploadów, domyślna drukarka).

## Uruchomienie lokalne
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Wejdź na `http://localhost:8000` (panel użytkownika) lub `http://localhost:8000/admin`.

## Docker
```bash
docker build -t drop2print .
docker run -p 8000:8000 -v $(pwd)/app/uploads:/app/app/uploads drop2print
```
> Uwaga: obraz domyślnie nie instaluje klienta CUPS. Dodaj `apt-get update && apt-get install -y cups-client` w Dockerfile, jeśli chcesz drukować z wnętrza kontenera.
> Używamy FastAPI/Pydantic v1 (zgodne z SQLModel) – po zmianie wersji Pythona przeinstaluj zależności (`pip install -r requirements.txt`).

## Docker Compose
```bash
docker compose up --build
```
Serwis startuje na porcie `8000`. Domyślnie montuje katalogi `app/uploads` i `app/db` z hosta, więc zadania i baza zostają zachowane między restartami. Jeśli chcesz wskazać drukarkę, ustaw zmienną `DROP2PRINT_PRINTER` w `docker-compose.yml` lub przy wywołaniu.

## Konfiguracja
- `DROP2PRINT_DB_PATH` – ścieżka do pliku bazy (domyślnie `app/db/drop2print.sqlite3`).
- `DROP2PRINT_UPLOAD_PATH` – katalog z zapisanymi plikami (domyślnie `app/uploads`).
- `DROP2PRINT_PRINTER` – nazwa drukarki dla `lp`; jeśli puste, użyje domyślnej.
