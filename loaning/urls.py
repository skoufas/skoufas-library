"""Loaning related URLs."""
from django.urls.resolvers import URLPattern
from django.urls.resolvers import URLResolver

# from django.urls import path
# from loaning import views

# home_list_view = views.HomeListView.as_view(
#     context_object_name="message_list",
#     template_name="books/home.html",
# )

urlpatterns: list[URLPattern | URLResolver] = [
    # path("", home_list_view, name="home"),
    # path("hello/<name>", views.hello_there, name="hello_there"),
    # path("about/", views.about, name="about"),
    # path("contact/", views.contact, name="contact"),
    # path("log/", views.log_message, name="log"),
]
