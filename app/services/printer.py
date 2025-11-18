import logging
from typing import Optional

import subprocess

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
            subprocess.run(cmd, check=True)
            logger.info("Sent job %s to printer %s", job.id, self.printer_name or "<default>")
        except FileNotFoundError:
            logger.warning("`lp` command not found; skipping real print for job %s", job.id)
        except subprocess.CalledProcessError as exc:
            logger.error("Printing failed for job %s: %s", job.id, exc)
            raise
