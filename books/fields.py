from books.validators import ISBNValidator, ISSNValidator, EANValidator
from django.db.models import CharField
from django.utils.translation import gettext_lazy as _
from django.core.validators import EMPTY_VALUES


class ISBNField(CharField):

    description = _("ISBN-10 or ISBN-13")

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 28
        kwargs["verbose_name"] = "ISBN"
        kwargs["validators"] = [ISBNValidator]
        super(ISBNField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            "min_length": 10,
            "validators": [ISBNValidator],
        }
        defaults.update(kwargs)
        return super(ISBNField, self).formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup"""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            cleaned_isbn = value.replace(" ", "").replace("-", "").upper()
            setattr(model_instance, self.attname, cleaned_isbn)
        return super(ISBNField, self).pre_save(model_instance, add)

    def __unicode__(self) -> str:
        return self.value


class ISSNField(CharField):

    description = _("ISSN")

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 16
        kwargs["verbose_name"] = "ISSN"
        kwargs["validators"] = [ISSNValidator]
        super(ISSNField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            "min_length": 8,
            "validators": [ISSNValidator],
        }
        defaults.update(kwargs)
        return super(ISSNField, self).formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup"""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            cleaned_issn = value.replace(" ", "").replace("-", "").upper()
            setattr(model_instance, self.attname, cleaned_issn)
        return super(ISSNField, self).pre_save(model_instance, add)

    def __unicode__(self) -> str:
        return self.value


class EANField(CharField):

    description = _("EAN-14, EAN-13, EAN-12, EAN-8")

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 28
        kwargs["verbose_name"] = "EAN"
        kwargs["validators"] = [EANValidator]
        super(EANField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            "min_length": 8,
            "validators": [EANValidator],
        }
        defaults.update(kwargs)
        return super(EANField, self).formfield(**defaults)

    def pre_save(self, model_instance, add):
        """Cleanup"""
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            cleaned_ean = value.replace(" ", "").replace("-", "").upper()
            setattr(model_instance, self.attname, cleaned_ean)
        return super(EANField, self).pre_save(model_instance, add)

    def __unicode__(self) -> str:
        return self.value
