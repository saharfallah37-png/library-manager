from datetime import date

from django.contrib import messages
from django.http import Http404
from django.shortcuts import render, redirect

from .sample_data import books, members, borrowings
from .storage import load_data, save_data


load_data()

def home(request):
    return render(request, "library/home.html")


def book_list(request):
    query = request.GET.get("q", "").strip()

    filtered_books = books

    if query:
        filtered_books = []

        for book in books:
            title_matches = query.casefold() in book["title"].casefold()
            author_matches = query.casefold() in book["author"].casefold()

            if title_matches or author_matches:
                filtered_books.append(book)

    context = {
        "books": filtered_books,
        "query": query,
    }

    return render(request, "library/book_list.html", context)


def member_list(request):
    context = {
        "members": members,
    }

    return render(request, "library/member_list.html", context)


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
                if year < 1 or year > 9999:
                    error = "سال انتشار باید بین ۱ و ۹۹۹۹ باشد."

        if not error:
            new_id = max(
                (book["id"] for book in books),
                default=0,
            ) + 1

            books.append({
                "id": new_id,
                "title": title,
                "author": author,
                "year": year,
                "available": True,
                "borrow_count": 0,
            })

            save_data()

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


def borrow_book(request):
    error = ""

    selected_book_id = request.GET.get("book_id", "")
    selected_member_id = ""

    if request.method == "POST":
        selected_book_id = request.POST.get("book_id", "")
        selected_member_id = request.POST.get("member_id", "")

        try:
            book_id = int(selected_book_id)
            member_id = int(selected_member_id)

        except ValueError:
            error = "لطفاً یک کتاب و یک عضو انتخاب کنید."

        else:
            selected_book = None
            selected_member = None

            for book in books:
                if book["id"] == book_id:
                    selected_book = book
                    break

            for member in members:
                if member["id"] == member_id:
                    selected_member = member
                    break

            if selected_book is None:
                error = "کتاب انتخاب‌شده پیدا نشد."

            elif selected_member is None:
                error = "عضو انتخاب‌شده پیدا نشد."

            elif not selected_book["available"]:
                error = "این کتاب قبلاً امانت داده شده است."

            else:
                selected_book["available"] = False
                selected_book["borrow_count"] += 1

                borrowings.append({
                    "book_id": book_id,
                    "member_id": member_id,
                    "borrowed_at": date.today().isoformat(),
                    "returned_at": None,
                })

                save_data()

                messages.success(
                    request,
                    "امانت کتاب با موفقیت ثبت شد.",
                )

                return redirect("book_list")

    available_books = []

    for book in books:
        if book["available"]:
            available_books.append(book)

    context = {
        "books": available_books,
        "members": members,
        "error": error,
        "selected_book_id": selected_book_id,
        "selected_member_id": selected_member_id,
    }

    return render(request, "library/borrow_book.html", context)


def return_book(request):
    error = ""

    if request.method == "POST":
        try:
            book_id = int(request.POST.get("book_id", ""))

        except ValueError:
            error = "لطفاً یک کتاب انتخاب کنید."

        else:
            selected_book = None

            for book in books:
                if book["id"] == book_id:
                    selected_book = book
                    break

            if selected_book is None:
                error = "کتاب انتخاب‌شده پیدا نشد."

            elif selected_book["available"]:
                error = "این کتاب قبلاً بازگردانده شده است."

            else:
                active_borrowing = None

                for borrowing in borrowings:
                    if (
                        borrowing["book_id"] == book_id
                        and borrowing["returned_at"] is None
                    ):
                        active_borrowing = borrowing
                        break

                if active_borrowing is None:
                    error = "سابقه‌ی امانت فعال برای این کتاب پیدا نشد."

                else:
                    active_borrowing["returned_at"] = date.today().isoformat()
                    selected_book["available"] = True
                    save_data()
                    messages.success(
                        request,
                        "بازگشت کتاب ثبت شد؛ کتاب دوباره قابل امانت است.",
                    )

                    return redirect("book_list")

    borrowed_books = []

    for book in books:
        if not book["available"]:
            borrowed_books.append(book)

    context = {
        "books": borrowed_books,
        "error": error,
    }

    return render(request, "library/return_book.html", context)


def member_history(request, member_id):
    member = None

    for item in members:
        if item["id"] == member_id:
            member = item
            break

    if member is None:
        raise Http404("عضو پیدا نشد.")

    active_borrowings = []
    returned_borrowings = []

    for borrowing in borrowings:
        if borrowing["member_id"] != member_id:
            continue

        book_title = "کتاب حذف‌شده یا نامشخص"

        for book in books:
            if book["id"] == borrowing["book_id"]:
                book_title = book["title"]
                break

        record = {
            "book_title": book_title,
            "borrowed_at": borrowing["borrowed_at"],
            "returned_at": borrowing["returned_at"],
        }

        if record["returned_at"] is None:
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
    total_books = len(books)
    total_members = len(members)

    available_books = sum(
        1 for book in books if book["available"]
    )

    borrowed_books = total_books - available_books

    total_borrows = sum(
        book.get("borrow_count", 0) for book in books
    )

    highest_count = max(
        (book.get("borrow_count", 0) for book in books),
        default=0,
    )

    most_borrowed_books = []

    if highest_count > 0:
        most_borrowed_books = [
            book
            for book in books
            if book.get("borrow_count", 0) == highest_count
        ]

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