from django.db import models
from django.utils import timezone


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    year = models.PositiveIntegerField()

    available = models.BooleanField(default=True)
    borrow_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title


class Member(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Borrowing(models.Model):
    book = models.ForeignKey(
        Book,
        on_delete=models.PROTECT,
        related_name="borrowings",
    )

    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="borrowings",
    )

    borrowed_at = models.DateField(
        default=timezone.localdate
    )

    returned_at = models.DateField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-borrowed_at", "-id"]

        constraints = [
            models.UniqueConstraint(
                fields=["book"],
                condition=models.Q(
                    returned_at__isnull=True
                ),
                name="one_active_borrowing_per_book",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(returned_at__isnull=True)
                    | models.Q(
                        returned_at__gte=models.F("borrowed_at")
                    )
                ),
                name="return_date_not_before_borrow_date",
            ),
        ]

    def __str__(self):
        return f"{self.book.title} — {self.member.name}"