import stdnum.exceptions
import stdnum.isbn
import stdnum.issn
import stdnum.ean
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def ISBNValidator(raw_isbn):

    if not isinstance(raw_isbn, str):
        raise ValidationError(_("Invalid ISBN: Not a string"))

    isbn = raw_isbn.replace("-", "").replace(" ", "")

    try:
        stdnum.isbn.validate(isbn)
    except stdnum.exceptions.InvalidChecksum:
        raise ValidationError(_("Invalid ISBN: wrong checksum"))
    except stdnum.exceptions.InvalidComponent:
        raise ValidationError(_("Invalid ISBN: component not one of 978, 979"))
    except stdnum.exceptions.InvalidLength:
        raise ValidationError(_("Invalid ISBN: length not 10 or 13"))
    except stdnum.exceptions.InvalidFormat:
        raise ValidationError(_("Invalid ISBN"))

    if isbn != isbn.upper():
        raise ValidationError(_("Invalid ISBN: Only upper case allowed"))

    return True


def ISSNValidator(raw_issn):

    if not isinstance(raw_issn, str):
        raise ValidationError(_("Invalid ISSN: Not a string"))

    issn = raw_issn.replace("-", "").replace(" ", "")

    try:
        stdnum.issn.validate(issn)
    except stdnum.exceptions.InvalidChecksum:
        raise ValidationError(_("Invalid ISSN: wrong checksum"))
    except stdnum.exceptions.InvalidLength:
        raise ValidationError(_("Invalid ISSN: length not 8"))
    except stdnum.exceptions.InvalidFormat:
        raise ValidationError(_("Invalid ISSN"))

    if issn != issn.upper():
        raise ValidationError(_("Invalid ISSN: Only upper case allowed"))

    return True


def EANValidator(raw_ean):

    if not isinstance(raw_ean, str):
        raise ValidationError(_("Invalid EAN: Not a string"))

    ean = raw_ean.replace("-", "").replace(" ", "")

    try:
        stdnum.ean.validate(ean)
    except stdnum.exceptions.InvalidChecksum:
        raise ValidationError(_("Invalid EAN: wrong checksum"))
    except stdnum.exceptions.InvalidLength:
        raise ValidationError(_("Invalid EAN: length not one of 14, 13, 12, 8"))
    except stdnum.exceptions.InvalidFormat:
        raise ValidationError(_("Invalid EAN"))

    if ean != ean.upper():
        raise ValidationError(_("Invalid EAN: Only upper case allowed"))

    return True
