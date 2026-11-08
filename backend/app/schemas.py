"""Schema validasi input/output (Pydantic v2).

Prinsip: jangan pernah percaya input client. Semua field divalidasi
tipe, panjang, dan karakter yang diizinkan sebelum menyentuh layer DB.
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

# Larang seluruh karakter kontrol C0/C1 kecuali tidak ada yang dibutuhkan.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)

    @field_validator("title")
    @classmethod
    def title_must_be_single_line_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Judul task tidak boleh kosong.")
        if _CONTROL_CHARS.search(cleaned):
            raise ValueError("Judul task mengandung karakter tidak diizinkan.")
        return cleaned


class TaskUpdate(BaseModel):
    completed: StrictBool


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    completed: bool
    created_at: datetime


class VersionOut(BaseModel):
    app: str
    version: str
    color: str
