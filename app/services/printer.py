import logging
import subprocess
from typing import Optional

from app.models import PrintJob

logger = logging.getLogger(__name__)


class PrinterService:
    """
    Lightweight wrapper around the system print command.

    Tries to use `lp` (CUPS). If unavailable, logs the action so the system can
    be wired later.
    """

    def __init__(self, printer_name: Optional[str] = None) -> None:
        self.printer_name = printer_name

    def print_file(self, job: PrintJob) -> None:
        cmd = ["lp", "-n", str(job.copies), job.storage_path]
        if self.printer_name:
            cmd.extend(["-d", self.printer_name])

        try:
            logger.info("Running command: %s", " ".join(cmd))
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            logger.warning("`lp` command not found; skipping real print for job %s", job.id)
            raise
        except subprocess.CalledProcessError as exc:
            logger.error("Printing failed for job %s: %s", job.id, exc)
            raise
