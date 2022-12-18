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

    pass


@admin.register(Customer)
class CustomerAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    """Customisation for Customer."""

    inlines = [
        LoanInline,
    ]
