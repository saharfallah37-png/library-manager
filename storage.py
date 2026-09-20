import json
import os
import tempfile
from pathlib import Path

from .sample_data import books, members, borrowings


DATA_FILE = Path(__file__).resolve().parent.parent / "data.json"


def save_data():
    data = {
        "books": books,
        "members": members,
        "borrowings": borrowings,
    }

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=DATA_FILE.parent,
            prefix="library_data_",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )

        os.replace(temporary_path, DATA_FILE)

    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def load_data():
    if not DATA_FILE.exists():
        save_data()
        return

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            "فایل data.json قابل خواندن نیست. "
            "ساختار فایل را بررسی کنید؛ اطلاعات آن بازنویسی نشد."
        ) from error

    if not isinstance(data, dict):
        raise ValueError("ساختار اصلی data.json باید یک دیکشنری باشد.")

    required_fields = {
        "books": {
            "id", "title", "author", "year",
            "available", "borrow_count",
        },
        "members": {
            "id", "name", "email",
        },
        "borrowings": {
            "book_id", "member_id", "borrowed_at", "returned_at",
        },
    }

    for collection_name, fields in required_fields.items():
        records = data.get(collection_name)

        if not isinstance(records, list):
            raise ValueError(
                f"بخش {collection_name} در data.json باید یک لیست باشد."
            )

        for record in records:
            if not isinstance(record, dict) or not fields.issubset(record):
                raise ValueError(
                    f"یکی از رکوردهای {collection_name} ناقص است."
                )

    books[:] = data["books"]
    members[:] = data["members"]
    borrowings[:] = data["borrowings"]