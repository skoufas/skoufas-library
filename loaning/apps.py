from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LoaningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "loaning"
    verbose_name = _("loaning")
