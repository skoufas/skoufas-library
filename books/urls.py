"""Book related URLs."""
from django.urls import path
from django.urls.resolvers import URLPattern
from django.urls.resolvers import URLResolver

from books import views

# home_list_view = views.HomeListView.as_view(
#     context_object_name="message_list",
#     template_name="books/home.html",
# )

app_name = "books"
urlpatterns: list[URLPattern | URLResolver] = [
    path(r"by-db-id/<int:pk>", views.BookEntryDetailView.as_view(), name="book-by-id"),
    path(r"by-entry-number/<int:pk>", views.BookEntryByEntryNumberDetailView.as_view(), name="book-by-entry-number"),
    # path("about/", views.about, name="about"),
    # path("contact/", views.contact, name="contact"),
    # path("log/", views.log_message, name="log"),
]
