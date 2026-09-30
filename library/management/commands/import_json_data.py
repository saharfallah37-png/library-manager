import json
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from library.models import Book, Borrowing, Member


class Command(BaseCommand):
    help = "Import existing data.json into empty library tables."

    # این دستور مستقل از بررسی URLها و ویوهای قدیمی اجرا می‌شود.
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the import without keeping database changes.",
        )

    def handle(self, *args, **options):
        path = settings.BASE_DIR / "data.json"

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise CommandError(
                f"خواندن data.json ناموفق بود: {error}"
            ) from error

        if not isinstance(data, dict):
            raise CommandError("ساختار اصلی JSON باید دیکشنری باشد.")

        for name in ("books", "members", "borrowings"):
            if not isinstance(data.get(name), list):
                raise CommandError(
                    f"بخش {name} باید یک لیست باشد."
                )

        location = "شروع انتقال"

        try:
            with transaction.atomic():
                if (
                    Book.objects.exists()
                    or Member.objects.exists()
                    or Borrowing.objects.exists()
                ):
                    raise CommandError(
                        "جدول‌های کتابخانه خالی نیستند؛ "
                        "هیچ اطلاعاتی تغییر نکرد."
                    )

                for index, item in enumerate(data["books"], start=1):
                    location = f"کتاب شمارهٔ {index}"

                    if type(item["id"]) is not int or item["id"] < 1:
                        raise ValueError("شناسهٔ کتاب معتبر نیست.")

                    if type(item["available"]) is not bool:
                        raise ValueError("وضعیت موجودی باید true یا false باشد.")

                    book = Book(
                        id=item["id"],
                        title=item["title"],
                        author=item["author"],
                        year=item["year"],
                        available=item["available"],
                        borrow_count=item["borrow_count"],
                    )

                    book.full_clean()
                    book.save(force_insert=True)

                for index, item in enumerate(data["members"], start=1):
                    location = f"عضو شمارهٔ {index}"

                    if type(item["id"]) is not int or item["id"] < 1:
                        raise ValueError("شناسهٔ عضو معتبر نیست.")

                    member = Member(
                        id=item["id"],
                        name=item["name"],
                        email=item["email"],
                    )

                    member.full_clean()
                    member.save(force_insert=True)

                for index, item in enumerate(
                    data["borrowings"], start=1
                ):
                    location = f"سابقهٔ امانت شمارهٔ {index}"
                    returned_at = item["returned_at"]

                    borrowing = Borrowing(
                        book_id=item["book_id"],
                        member_id=item["member_id"],
                        borrowed_at=date.fromisoformat(
                            item["borrowed_at"]
                        ),
                        returned_at=(
                            date.fromisoformat(returned_at)
                            if returned_at is not None
                            else None
                        ),
                    )

                    borrowing.full_clean()
                    borrowing.save(force_insert=True)

                location = "بررسی نهایی موجودی"

                for book in Book.objects.all():
                    has_active_borrowing = book.borrowings.filter(
                        returned_at__isnull=True
                    ).exists()

                    if book.available != (not has_active_borrowing):
                        raise ValueError(
                            f"موجودی کتاب {book.pk} با امانت‌ها سازگار نیست."
                        )

                counts = (
                    Book.objects.count(),
                    Member.objects.count(),
                    Borrowing.objects.count(),
                )

                if options["dry_run"]:
                    transaction.set_rollback(True)

        except (
            ValidationError,
            IntegrityError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ) as error:
            raise CommandError(
                f"خطا در {location}: {error}\n"
                "انتقال لغو شد؛ هیچ رکوردی از این اجرا باقی نماند."
            ) from error

        if options["dry_run"]:
            message = (
                "بررسی آزمایشی موفق بود؛ "
                "اطلاعات در پایگاه داده ذخیره نشد."
            )
        else:
            message = "اطلاعات JSON با موفقیت به SQLite منتقل شد."

        self.stdout.write(self.style.SUCCESS(message))
        self.stdout.write(f"Books: {counts[0]}")
        self.stdout.write(f"Members: {counts[1]}")
        self.stdout.write(f"Borrowings: {counts[2]}")