import enum
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Column, String


class PrintStatus(str, enum.Enum):
    pending = "pending"
    printed = "printed"
    failed = "failed"


class PrintJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    storage_path: str
    copies: int = Field(default=1, ge=1)
    status: PrintStatus = Field(default=PrintStatus.pending)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    printed_at: Optional[datetime] = Field(default=None)
    error: Optional[str] = Field(default=None)


class Setting(SQLModel, table=True):
    key: str = Field(sa_column=Column("key", String, primary_key=True, unique=True))
    value: str

    @staticmethod
    def default_copies() -> int:
        return 1
