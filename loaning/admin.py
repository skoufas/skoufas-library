"""Book Loaning admin section customisation."""

from django.contrib import admin
from djangoql.admin import DjangoQLSearchMixin

from .models import Customer
from .models import Loan


class LoanInline(admin.TabularInline):
    """Customisation for Loan."""

    model = Loan


@admin.register(Loan)
class LoanAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Loan."""

    list_display = ["customer", "entry_number", "status", "start", "expected_end", "end"]
    list_filter = ["status", "start", "expected_end", "end"]
    autocomplete_fields = ["customer", "entry_number"]


@admin.register(Customer)
class CustomerAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Customer."""

    inlines = [
        LoanInline,
    ]

    search_fields = [
        "surname",
        "first_name",
        "middle_name",
        "phone_number",
        "email",
        "id_number",
    ]
