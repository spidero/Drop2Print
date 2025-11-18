from fastapi import Request

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
