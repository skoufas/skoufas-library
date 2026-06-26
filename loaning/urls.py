"""Loaning related URLs."""

from django.urls import path
from django.urls.resolvers import URLPattern
from django.urls.resolvers import URLResolver

from loaning import views

app_name = "loaning"  # pylint: disable=invalid-name
urlpatterns: list[URLPattern | URLResolver] = [
    path("", views.LoanDeskView.as_view(), name="loan-desk"),
    path("loans/<int:pk>/", views.LoanDetailView.as_view(), name="loan-detail"),
    path("customers/", views.CustomerListView.as_view(), name="customer-list"),
    path("customers/new/", views.CustomerCreateView.as_view(), name="customer-create"),
    path("customers/<int:pk>/edit/", views.CustomerUpdateView.as_view(), name="customer-edit"),
    path("customers/<int:pk>/delete/", views.CustomerDeleteView.as_view(), name="customer-delete"),
    path("customers/export/koha.csv", views.KohaPatronExportView.as_view(), name="customer-export-koha"),
]
