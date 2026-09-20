from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("books/", views.book_list, name="book_list"),
    path("members/", views.member_list, name="member_list"),
    path("borrow/", views.borrow_book, name="borrow_book"),
    path("return/", views.return_book, name="return_book"),
    path("members/<int:member_id>/history/",views.member_history,name="member_history",),
    path("statistics/", views.statistics, name="statistics"),
    path("books/add/", views.add_book, name="add_book"),
]