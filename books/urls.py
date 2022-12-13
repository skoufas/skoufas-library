from django.urls import path
from django.views.generic import TemplateView

from books import views

# home_list_view = views.HomeListView.as_view(
#     context_object_name="message_list",
#     template_name="books/home.html",
# )

urlpatterns: list[path] = [
    path("", TemplateView.as_view(template_name="skoufas_library/home.html"), name="home"),
    path("about/", TemplateView.as_view(template_name="skoufas_library/about.html"), name="about"),
    path("contact/", TemplateView.as_view(template_name="skoufas_library/contact.html"), name="contact"),
    # path("hello/<name>", views.hello_there, name="hello_there"),
    # path("about/", views.about, name="about"),
    # path("contact/", views.contact, name="contact"),
    # path("log/", views.log_message, name="log"),
]
