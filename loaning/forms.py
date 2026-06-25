"""Forms for the loaning app."""

import datetime

from django import forms
from django.db import transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from books.models import EntryNumber
from loaning.models import Customer
from loaning.models import Loan


class CustomerForm(forms.ModelForm):
    """Form for creating and editing a Customer."""

    def __init__(self, *args, **kwargs):
        """Require customer ID document fields in the custom workflow."""
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["id_type"].widget.attrs["class"] = "form-select"
        self.fields["first_name"].required = True
        self.fields["surname"].required = True
        self.fields["id_type"].required = True
        self.fields["id_number"].required = True

    class Meta:
        """Meta for CustomerForm."""

        model = Customer
        fields = [
            "first_name",
            "middle_name",
            "surname",
            "id_type",
            "id_number",
            "phone_number",
            "email",
            "address",
            "skoufas_member_id",
        ]


class LoanCheckoutForm(forms.Form):
    """Form for creating a loan from the loan desk."""

    customer_id = forms.IntegerField(widget=forms.HiddenInput)
    entry_number_id = forms.IntegerField(widget=forms.HiddenInput)
    start = forms.DateField(
        label=_("start"), initial=datetime.date.today, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    )
    expected_end = forms.DateField(
        label=_("expected end"),
        initial=lambda: datetime.date.today() + datetime.timedelta(days=60),
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    note = forms.CharField(label=_("note"), required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def clean(self):
        """Validate checkout dates, customer, and copy availability."""
        cleaned_data = super().clean()
        customer_id = cleaned_data.get("customer_id")
        entry_number_id = cleaned_data.get("entry_number_id")
        start = cleaned_data.get("start")
        expected_end = cleaned_data.get("expected_end")
        if start and expected_end and expected_end < start:
            self.add_error("expected_end", _("Expected return date cannot be before the start date."))
        if customer_id and not Customer.objects.filter(pk=customer_id).exists():
            self.add_error("customer_id", _("Selected customer no longer exists."))
        if entry_number_id:
            try:
                entry_number = EntryNumber.objects.get(pk=entry_number_id)
            except EntryNumber.DoesNotExist:
                self.add_error("entry_number_id", _("Selected entry number no longer exists."))
            else:
                if (entry_number.copies or 0) < 1:
                    self.add_error(
                        "entry_number_id", _("This entry number is not borrowable because it has no copies.")
                    )
                elif available_copies(entry_number) < 1:
                    self.add_error("entry_number_id", _("No copies are available for loan."))
        return cleaned_data

    def as_bootstrap(self):
        """Apply Bootstrap classes to visible fields."""
        for field_name in ["start", "expected_end", "note"]:
            self.fields[field_name].widget.attrs.setdefault("class", "form-control")
        return self

    def save(self):
        """Create the active loan."""
        return Loan.objects.create(
            customer_id=self.cleaned_data["customer_id"],
            entry_number_id=self.cleaned_data["entry_number_id"],
            start=self.cleaned_data["start"],
            expected_end=self.cleaned_data["expected_end"],
            note=self.cleaned_data["note"],
        )


class LoanReturnForm(forms.Form):
    """Form for returning an active loan."""

    end = forms.DateField(label=_("end"), initial=datetime.date.today, widget=forms.DateInput(attrs={"type": "date"}))
    note = forms.CharField(label=_("note"), required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, loan=None, **kwargs):
        """Store the loan being returned."""
        self.loan = loan
        super().__init__(*args, **kwargs)
        self.fields["end"].widget.attrs.setdefault("class", "form-control")
        self.fields["note"].widget.attrs.setdefault("class", "form-control")

    def clean_end(self):
        """Validate the return date."""
        end = self.cleaned_data["end"]
        if self.loan and end < self.loan.start:
            raise forms.ValidationError(_("Return date cannot be before the start date."))
        return end

    def save(self):
        """Mark the loan returned."""
        self.loan.status = Loan.STATUS_RETURNED
        self.loan.end = self.cleaned_data["end"]
        if self.cleaned_data["note"]:
            self.loan.note = self.cleaned_data["note"]
        self.loan.save(update_fields=["status", "end", "note"])
        return self.loan


class LoanExceptionForm(LoanReturnForm):
    """Form for closing a loan as lost or cancelled."""

    def save_lost(self):
        """Mark a loan lost and reduce the entry number inventory."""
        with transaction.atomic():
            entry_number = self.loan.entry_number
            if self.loan.status == Loan.STATUS_ACTIVE and entry_number.copies and entry_number.copies > 0:
                EntryNumber.objects.filter(pk=entry_number.pk).update(copies=F("copies") - 1)
            self.loan.status = Loan.STATUS_LOST
            self.loan.end = self.cleaned_data["end"]
            if self.cleaned_data["note"]:
                self.loan.note = self.cleaned_data["note"]
            self.loan.save(update_fields=["status", "end", "note"])
        return self.loan

    def save_cancelled(self):
        """Mark a loan cancelled."""
        self.loan.status = Loan.STATUS_CANCELLED
        self.loan.end = self.cleaned_data["end"]
        if self.cleaned_data["note"]:
            self.loan.note = self.cleaned_data["note"]
        self.loan.save(update_fields=["status", "end", "note"])
        return self.loan


def active_loan_count(entry_number):
    """Count active loans for an entry number."""
    return Loan.objects.filter(entry_number=entry_number, status=Loan.STATUS_ACTIVE).count()


def available_copies(entry_number):
    """Return available copies for an entry number."""
    return max((entry_number.copies or 0) - active_loan_count(entry_number), 0)
