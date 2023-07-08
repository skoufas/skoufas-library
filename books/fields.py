"""Custom Fields for books."""
from django.core.validators import EMPTY_VALUES
from django.db.models import CharField
from django.utils.translation import gettext_lazy as _

from books.validators import validate_ean
from books.validators import validate_isbn
from books.validators import validate_issn
from books.validators import validate_skoufas_classification


class ISBNField(CharField):
    """Custom Field for ISBN values."""

    description = _("ISBN-10 or ISBN-13")

    def __init__(self, *args, **kwargs):
        """Construct a field."""
        kwargs["max_length"] = 28
        kwargs["verbose_name"] = _("ISBN")
        kwargs["validators"] = [validate_isbn]
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        """Construct a form field."""
        defaults = {
            "min_length": 10,
            "validators": [validate_isbn],
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup."""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            cleaned_isbn = value.replace(" ", "").replace("-", "").upper()
            setattr(model_instance, self.attname, cleaned_isbn)
        return super().pre_save(model_instance, add)


class ISSNField(CharField):
    """Custom Field for ISSN values."""

    description = _("ISSN")

    def __init__(self, *args, **kwargs):
        """Construct a field."""
        kwargs["max_length"] = 16
        kwargs["verbose_name"] = _("ISSN")
        kwargs["validators"] = [validate_issn]
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        """Construct a form field."""
        defaults = {
            "min_length": 8,
            "validators": [validate_issn],
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup."""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            cleaned_issn = value.replace(" ", "").replace("-", "").upper()
            setattr(model_instance, self.attname, cleaned_issn)
        return super().pre_save(model_instance, add)


class EANField(CharField):
    """Custom Field for EAN values."""

    description = _("EAN-14, EAN-13, EAN-12, EAN-8")

    def __init__(self, *args, **kwargs):
        """Construct a field."""
        kwargs["max_length"] = 28
        kwargs["verbose_name"] = _("EAN")
        kwargs["validators"] = [validate_ean]
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        """Construct a form field."""
        defaults = {
            "min_length": 8,
            "validators": [validate_ean],
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup."""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            cleaned_ean = value.replace(" ", "").replace("-", "").upper()
            setattr(model_instance, self.attname, cleaned_ean)
        return super().pre_save(model_instance, add)


class SkoufasClassificationField(CharField):
    """Custom Field for skoufas classification values."""

    description = _("Skoufas classification format XXX, XXX ABC, XXX.XXX, XXX.XXX ABC")

    def __init__(self, *args, **kwargs):
        """Construct a field."""
        kwargs["max_length"] = 28
        kwargs["verbose_name"] = _("Classification")
        kwargs["validators"] = [validate_skoufas_classification]
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        """Construct a form field."""
        defaults = {
            "min_length": 3,
            "validators": [validate_skoufas_classification],
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup."""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            value = value.replace("  ", " ").replace("-", "").upper()
            setattr(model_instance, self.attname, value)
        return super().pre_save(model_instance, add)


class LanguageField(CharField):
    """A language field for Django models."""

    def __init__(self, *args, **kwargs):
        """Choice is one of languages defined."""
        # Local import so the languages aren't loaded unless they are needed.
        from .languages import LANGUAGES

        kwargs.setdefault("max_length", 3)
        kwargs.setdefault("choices", LANGUAGES)
        kwargs.setdefault("db_collation", None)

        super().__init__(*args, **kwargs)
