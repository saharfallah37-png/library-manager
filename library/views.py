from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Max, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Book, Borrowing, Member


def home(request):
    return render(request, "library/home.html")


def book_list(request):
    query = request.GET.get("q", "").strip()
    books = Book.objects.all()

    # حفظ رفتار جست‌وجوی قبلی، از جمله حروف فارسی و انگلیسی
    if query:
        search_text = query.casefold()
        books = [
            book
            for book in books
            if (
                search_text in book.title.casefold()
                or search_text in book.author.casefold()
            )
        ]

    return render(
        request,
        "library/book_list.html",
        {
            "books": books,
            "query": query,
        },
    )


def member_list(request):
    return render(
        request,
        "library/member_list.html",
        {"members": Member.objects.all()},
    )


def add_book(request):
    error = ""
    title = ""
    author = ""
    year_text = ""

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        author = request.POST.get("author", "").strip()
        year_text = request.POST.get("year", "").strip()

        if not title or not author:
            error = "عنوان کتاب و نام نویسنده نباید خالی باشند."
        else:
            try:
                year = int(year_text)
            except ValueError:
                error = "سال انتشار باید یک عدد صحیح باشد."
            else:
                if not 1 <= year <= 9999:
                    error = "سال انتشار باید بین ۱ و ۹۹۹۹ باشد."

        if not error:
            book = Book(
                title=title,
                author=author,
                year=year,
                available=True,
                borrow_count=0,
            )

            try:
                book.full_clean()
            except ValidationError as exc:
                error = " ".join(exc.messages)
            else:
                book.save()

                messages.success(
                    request,
                    "کتاب جدید با موفقیت به کتابخانه اضافه شد.",
                )
                return redirect("book_list")

    return render(
        request,
        "library/add_book.html",
        {
            "error": error,
            "title": title,
            "author": author,
            "year_text": year_text,
        },
    )


def parse_id(value):
    try:
        result = int(value)
    except (ValueError, TypeError):
        return None

    if 0 < result <= 9223372036854775807:
        return result

    return None


def borrow_book(request):
    error = ""
    selected_book_id = request.GET.get("book_id", "")
    selected_member_id = ""

    if request.method == "POST":
        selected_book_id = request.POST.get("book_id", "")
        selected_member_id = request.POST.get("member_id", "")

        book_id = parse_id(selected_book_id)
        member_id = parse_id(selected_member_id)

        if book_id is None or member_id is None:
            error = "لطفاً یک کتاب و یک عضو معتبر انتخاب کنید."
        else:
            book = Book.objects.filter(pk=book_id).first()
            member = Member.objects.filter(pk=member_id).first()

            if book is None:
                error = "کتاب انتخاب‌شده پیدا نشد."
            elif member is None:
                error = "عضو انتخاب‌شده پیدا نشد."
            elif not book.available:
                error = "این کتاب قبلاً امانت داده شده است."
            else:
                try:
                    with transaction.atomic():
                        updated = Book.objects.filter(
                            pk=book.pk,
                            available=True,
                        ).update(
                            available=False,
                            borrow_count=F("borrow_count") + 1,
                        )

                        if updated != 1:
                            raise IntegrityError(
                                "Book is no longer available."
                            )

                        Borrowing.objects.create(
                            book=book,
                            member=member,
                            borrowed_at=timezone.localdate(),
                        )

                except IntegrityError:
                    error = (
                        "امانت ثبت نشد؛ ممکن است کتاب "
                        "هم‌اکنون امانت داده شده باشد. "
                        "صفحه را تازه‌سازی کنید."
                    )
                else:
                    messages.success(
                        request,
                        "امانت کتاب با موفقیت ثبت شد.",
                    )
                    return redirect("book_list")

    return render(
        request,
        "library/borrow_book.html",
        {
            "books": Book.objects.filter(available=True),
            "members": Member.objects.all(),
            "error": error,
            "selected_book_id": selected_book_id,
            "selected_member_id": selected_member_id,
        },
    )


def return_book(request):
    error = ""

    if request.method == "POST":
        book_id = parse_id(request.POST.get("book_id", ""))

        if book_id is None:
            error = "لطفاً یک کتاب معتبر انتخاب کنید."
        else:
            book = Book.objects.filter(pk=book_id).first()

            if book is None:
                error = "کتاب انتخاب‌شده پیدا نشد."
            else:
                today = timezone.localdate()

                try:
                    with transaction.atomic():
                        returned_count = Borrowing.objects.filter(
                            book_id=book_id,
                            returned_at__isnull=True,
                            borrowed_at__lte=today,
                        ).update(returned_at=today)

                        if returned_count:
                            Book.objects.filter(pk=book_id).update(
                                available=True
                            )

                except IntegrityError:
                    error = "بازگشت کتاب ثبت نشد؛ دوباره بررسی کنید."
                else:
                    if returned_count:
                        messages.success(
                            request,
                            "بازگشت کتاب ثبت شد؛ "
                            "کتاب دوباره قابل امانت است.",
                        )
                        return redirect("book_list")

                    error = (
                        "امانت فعالی با تاریخ معتبر برای این کتاب "
                        "پیدا نشد؛ ممکن است قبلاً بازگردانده شده باشد."
                    )

    return render(
        request,
        "library/return_book.html",
        {
            "books": Book.objects.filter(available=False),
            "error": error,
        },
    )


def member_history(request, member_id):
    member = get_object_or_404(Member, pk=member_id)

    history = Borrowing.objects.filter(
        member=member
    ).select_related("book")

    active_borrowings = []
    returned_borrowings = []

    for borrowing in history:
        record = {
            "book_title": borrowing.book.title,
            "borrowed_at": borrowing.borrowed_at.isoformat(),
            "returned_at": (
                borrowing.returned_at.isoformat()
                if borrowing.returned_at
                else None
            ),
        }

        if borrowing.returned_at is None:
            active_borrowings.append(record)
        else:
            returned_borrowings.append(record)

    return render(
        request,
        "library/member_history.html",
        {
            "member": member,
            "active_borrowings": active_borrowings,
            "returned_borrowings": returned_borrowings,
        },
    )


def statistics(request):
    books = Book.objects.all()

    total_books = books.count()
    total_members = Member.objects.count()
    available_books = books.filter(available=True).count()
    borrowed_books = books.filter(available=False).count()

    summary = books.aggregate(
        total=Sum("borrow_count"),
        highest=Max("borrow_count"),
    )

    total_borrows = summary["total"] or 0
    highest_count = summary["highest"] or 0

    most_borrowed_books = (
        books.filter(borrow_count=highest_count)
        if highest_count > 0
        else books.none()
    )

    return render(
        request,
        "library/statistics.html",
        {
            "total_books": total_books,
            "total_members": total_members,
            "available_books": available_books,
            "borrowed_books": borrowed_books,
            "total_borrows": total_borrows,
            "highest_count": highest_count,
            "most_borrowed_books": most_borrowed_books,
        },
    )