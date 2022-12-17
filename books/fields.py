"""Custom Fields for books."""
from django.core.validators import EMPTY_VALUES
from django.db.models import CharField
from django.utils.translation import gettext_lazy as _

from books.validators import DeweyValidator
from books.validators import EANValidator
from books.validators import ISBNValidator
from books.validators import ISSNValidator


class ISBNField(CharField):
    """Custom Field for ISBN values."""

    description = _("ISBN-10 or ISBN-13")

    def __init__(self, *args, **kwargs):
        """Construct a field."""
        kwargs["max_length"] = 28
        kwargs["verbose_name"] = _("ISBN")
        kwargs["validators"] = [ISBNValidator]
        super(ISBNField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        """Construct a form field."""
        defaults = {
            "min_length": 10,
            "validators": [ISBNValidator],
        }
        defaults.update(kwargs)
        return super(ISBNField, self).formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup."""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            cleaned_isbn = value.replace(" ", "").replace("-", "").upper()
            setattr(model_instance, self.attname, cleaned_isbn)
        return super(ISBNField, self).pre_save(model_instance, add)

    # def __unicode__(self) -> str:
    #     """Return the field value."""
    #     return self.value


class ISSNField(CharField):
    """Custom Field for ISSN values."""

    description = _("ISSN")

    def __init__(self, *args, **kwargs):
        """Construct a field."""
        kwargs["max_length"] = 16
        kwargs["verbose_name"] = _("ISSN")
        kwargs["validators"] = [ISSNValidator]
        super(ISSNField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        """Construct a form field."""
        defaults = {
            "min_length": 8,
            "validators": [ISSNValidator],
        }
        defaults.update(kwargs)
        return super(ISSNField, self).formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup."""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            cleaned_issn = value.replace(" ", "").replace("-", "").upper()
            setattr(model_instance, self.attname, cleaned_issn)
        return super(ISSNField, self).pre_save(model_instance, add)

    # def __unicode__(self) -> str:
    #     """Return the field value."""
    #     return self.value


class EANField(CharField):
    """Custom Field for EAN values."""

    description = _("EAN-14, EAN-13, EAN-12, EAN-8")

    def __init__(self, *args, **kwargs):
        """Construct a field."""
        kwargs["max_length"] = 28
        kwargs["verbose_name"] = _("EAN")
        kwargs["validators"] = [EANValidator]
        super(EANField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        """Construct a form field."""
        defaults = {
            "min_length": 8,
            "validators": [EANValidator],
        }
        defaults.update(kwargs)
        return super(EANField, self).formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup."""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            cleaned_ean = value.replace(" ", "").replace("-", "").upper()
            setattr(model_instance, self.attname, cleaned_ean)
        return super(EANField, self).pre_save(model_instance, add)

    # def __unicode__(self) -> str:
    #     """Return the field value."""
    #     return self.value


class DeweyField(CharField):
    """Custom Field for Dewey values."""

    description = _("Dewey format XXX, XXX ABC, XXX.XXX, XXX.XXX ABC")

    def __init__(self, *args, **kwargs):
        """Construct a field."""
        kwargs["max_length"] = 28
        kwargs["verbose_name"] = _("Dewey")
        kwargs["validators"] = [DeweyValidator]
        super(DeweyField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        """Construct a form field."""
        defaults = {
            "min_length": 3,
            "validators": [DeweyValidator],
        }
        defaults.update(kwargs)
        return super(DeweyField, self).formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup."""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            value = value.replace("  ", " ").replace("-", "").upper()
            setattr(model_instance, self.attname, value)
        return super(DeweyField, self).pre_save(model_instance, add)

    # def __unicode__(self) -> str:
    #     """Return the field value."""
    #     return self.value
