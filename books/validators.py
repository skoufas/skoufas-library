"""Validators for book related values."""
import re

import stdnum.ean
import stdnum.exceptions
import stdnum.isbn
import stdnum.issn
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_isbn(raw_isbn):
    """Validate ISBN values."""
    if not isinstance(raw_isbn, str):
        raise ValidationError(_("Invalid ISBN: Not a string"))

    isbn = raw_isbn.replace("-", "").replace(" ", "")

    try:
        stdnum.isbn.validate(isbn)
    except stdnum.exceptions.InvalidChecksum as exc:
        raise ValidationError(_("Invalid ISBN: wrong checksum")) from exc
    except stdnum.exceptions.InvalidComponent as exc:
        raise ValidationError(_("Invalid ISBN: component not one of 978, 979")) from exc
    except stdnum.exceptions.InvalidLength as exc:
        raise ValidationError(_("Invalid ISBN: length not 10 or 13")) from exc
    except stdnum.exceptions.InvalidFormat as exc:
        raise ValidationError(_("Invalid ISBN")) from exc

    if isbn != isbn.upper():
        raise ValidationError(_("Invalid ISBN: Only upper case allowed"))

    return True


def validate_issn(raw_issn):
    """Validate ISSN values."""
    if not isinstance(raw_issn, str):
        raise ValidationError(_("Invalid ISSN: Not a string"))

    issn = raw_issn.replace("-", "").replace(" ", "")

    try:
        stdnum.issn.validate(issn)
    except stdnum.exceptions.InvalidChecksum as exc:
        raise ValidationError(_("Invalid ISSN: wrong checksum")) from exc
    except stdnum.exceptions.InvalidLength as exc:
        raise ValidationError(_("Invalid ISSN: length not 8")) from exc
    except stdnum.exceptions.InvalidFormat as exc:
        raise ValidationError(_("Invalid ISSN")) from exc

    if issn != issn.upper():
        raise ValidationError(_("Invalid ISSN: Only upper case allowed"))

    return True


def validate_ean(raw_ean):
    """Validate EAN values."""
    if not isinstance(raw_ean, str):
        raise ValidationError(_("Invalid EAN: Not a string"))

    ean = raw_ean.replace("-", "").replace(" ", "")

    try:
        stdnum.ean.validate(ean)
    except stdnum.exceptions.InvalidChecksum as exc:
        raise ValidationError(_("Invalid EAN: wrong checksum")) from exc
    except stdnum.exceptions.InvalidLength as exc:
        raise ValidationError(_("Invalid EAN: length not one of 14, 13, 12, 8")) from exc
    except stdnum.exceptions.InvalidFormat as exc:
        raise ValidationError(_("Invalid EAN")) from exc

    if ean != ean.upper():
        raise ValidationError(_("Invalid EAN: Only upper case allowed"))

    return True


strict_dewey_res = [
    re.compile(r"[0-9]{3}\.[0-9]{1,6} [A-ZΑ-Ω]+"),
    re.compile(r"[0-9]{3}\.[0-9]{1,6}"),
    re.compile(r"[0-9]{3} [A-ZΑ-Ω]+"),
    re.compile(r"[0-9]{3}"),
]


def validate_skoufas_dewey(raw_dewey):
    """Validate Dewey values according to skoufas library."""
    if not isinstance(raw_dewey, str):
        raise ValidationError(_("Invalid Dewey: Not a string"))

    if raw_dewey != raw_dewey.upper():
        raise ValidationError(_("Invalid Dewey: Only upper case allowed"))
    for dewey_re in strict_dewey_res:
        if dewey_re.fullmatch(raw_dewey):
            return True

    raise ValidationError(_("Invalid Dewey: Invalid format"))
