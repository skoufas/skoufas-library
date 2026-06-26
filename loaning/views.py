"""Views on Loaning."""

import csv
import datetime

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateResponseMixin

from books.models import EntryNumber
from loaning.forms import CustomerForm
from loaning.forms import LoanCheckoutForm
from loaning.forms import LoanExceptionForm
from loaning.forms import LoanReturnForm
from loaning.forms import available_copies
from loaning.models import Customer
from loaning.models import Loan


def _active_loan_filter():
    """Return the reusable active-loan query filter."""
    return Q(loan__status=Loan.STATUS_ACTIVE)


def _annotate_customer(customer):
    """Attach active-loan display data to a customer."""
    customer.active_loan_count = customer.loan_set.filter(status=Loan.STATUS_ACTIVE).count()
    customer.overdue_loan_count = customer.loan_set.filter(
        status=Loan.STATUS_ACTIVE, expected_end__lt=datetime.date.today()
    ).count()
    return customer


def _annotate_entry_number(entry_number):
    """Attach availability display data to an entry number."""
    entry_number.active_loan_count = entry_number.loan_set.filter(status=Loan.STATUS_ACTIVE).count()
    entry_number.available_copies = max((entry_number.copies or 0) - entry_number.active_loan_count, 0)
    return entry_number


def _customer_search(query):
    """Search customers for the loan desk."""
    if not query:
        return Customer.objects.none()
    today = datetime.date.today()
    return Customer.objects.filter(
        Q(surname__icontains=query)
        | Q(first_name__icontains=query)
        | Q(email__icontains=query)
        | Q(phone_number__icontains=query)
        | Q(id_number__icontains=query)
    ).annotate(
        active_loan_count=Count("loan", filter=_active_loan_filter()),
        overdue_loan_count=Count(
            "loan",
            filter=Q(loan__status=Loan.STATUS_ACTIVE, loan__expected_end__lt=today),
        ),
    )[:25]


def _entry_number_search(query):
    """Search entry numbers and related book metadata for the loan desk."""
    if not query:
        return EntryNumber.objects.none()
    return (
        EntryNumber.objects.filter(
            Q(entry_number__icontains=query)
            | Q(book_entry__title__icontains=query)
            | Q(book_entry__subtitle__icontains=query)
            | Q(book_entry__authors__organisation_name__icontains=query)
            | Q(book_entry__authors__surname__icontains=query)
            | Q(book_entry__authors__first_name__icontains=query)
            | Q(book_entry__isbn__icontains=query)
            | Q(book_entry__issn__icontains=query)
            | Q(book_entry__ean__icontains=query)
        )
        .select_related("book_entry")
        .prefetch_related("book_entry__authors")
        .annotate(active_loan_count=Count("loan", filter=_active_loan_filter(), distinct=True))
        .distinct()[:25]
    )


class CustomerListView(PermissionRequiredMixin, ListView):
    """List customers with optional name/phone search."""

    model = Customer
    permission_required = "loaning.view_customer"
    paginate_by = 50

    def get_queryset(self):
        """Filter by search query if provided."""
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(surname__icontains=q)
                | Q(first_name__icontains=q)
                | Q(phone_number__icontains=q)
                | Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        """Add search query to context."""
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        return context


class CustomerCreateView(PermissionRequiredMixin, CreateView):
    """Create a new customer."""

    model = Customer
    form_class = CustomerForm
    permission_required = ("loaning.add_customer", "loaning.change_customer")

    def get_success_url(self):
        """Redirect to the edit page of the newly created customer."""
        return reverse_lazy("loaning:customer-edit", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        """Show success message on create."""
        messages.success(self.request, _("Customer created successfully."))
        return super().form_valid(form)


class CustomerUpdateView(PermissionRequiredMixin, UpdateView):
    """Edit an existing customer."""

    model = Customer
    form_class = CustomerForm
    permission_required = "loaning.change_customer"

    def get_success_url(self):
        """Stay on the edit page after saving."""
        return reverse_lazy("loaning:customer-edit", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        """Add customer loan history."""
        context = super().get_context_data(**kwargs)
        context["active_loans"] = self.object.loan_set.filter(status=Loan.STATUS_ACTIVE).select_related(
            "entry_number", "entry_number__book_entry"
        )
        context["closed_loans"] = self.object.loan_set.exclude(status=Loan.STATUS_ACTIVE).select_related(
            "entry_number", "entry_number__book_entry"
        )[:25]
        return context

    def form_valid(self, form):
        """Show success message on update."""
        messages.success(self.request, _("Customer saved successfully."))
        return super().form_valid(form)


class CustomerDeleteView(PermissionRequiredMixin, DeleteView):
    """Delete a customer who has no active loans."""

    model = Customer
    permission_required = "loaning.delete_customer"
    success_url = reverse_lazy("loaning:customer-list")

    def post(self, request, *args, **kwargs):
        """Block deletion if the customer has active loans."""
        self.object = self.get_object()
        if self.object.loan_set.filter(status=Loan.STATUS_ACTIVE).exists():
            messages.error(request, _("Customers with active loans cannot be deleted."))
            return redirect("loaning:customer-edit", pk=self.object.pk)
        with transaction.atomic():
            self.object.loan_set.update(customer=None)
            messages.success(request, _("Customer deleted and closed loans anonymized."))
            return super().post(request, *args, **kwargs)


class KohaPatronExportView(View):
    """Stream all patrons as a Koha-compatible patron import CSV."""

    KOHA_BRANCH = "SKOUFAS"
    KOHA_CATEGORY = "PT"

    COLUMNS = [
        "cardnumber",
        "surname",
        "firstname",
        "othernames",
        "address",
        "phone",
        "email",
        "branchcode",
        "categorycode",
        "borrowernotes",
        "sort1",
    ]

    class Echo:
        """File-like object that returns written values directly."""

        def write(self, value):
            return value

    def _customer_to_row(self, customer: Customer) -> list:
        cardnumber = str(customer.pk)
        borrowernotes = ""
        if customer.id_type and customer.id_number:
            borrowernotes = f"{customer.id_type}: {customer.id_number}"
        elif customer.id_number:
            borrowernotes = customer.id_number
        return [
            cardnumber,
            customer.surname,
            customer.first_name,
            customer.middle_name or "",
            customer.address,
            customer.phone_number,
            customer.email,
            self.KOHA_BRANCH,
            self.KOHA_CATEGORY,
            borrowernotes,
            customer.skoufas_member_id or "",
        ]

    async def _rows(self):
        writer = csv.writer(self.Echo())
        yield writer.writerow(self.COLUMNS)
        async for customer in Customer.objects.order_by("surname", "first_name").all():
            yield writer.writerow(self._customer_to_row(customer))

    async def get(self, request):
        user = await request.auser()
        if not user.is_authenticated:
            from django.conf import settings

            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        if not user.has_perm("loaning.view_customer"):
            raise PermissionDenied
        return StreamingHttpResponse(
            streaming_content=self._rows(),
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="koha-patrons.csv"'},
        )


class LoanDeskView(PermissionRequiredMixin, TemplateResponseMixin, View):
    """Loan desk for searching customers/books, checking out, and returning loans."""

    template_name = "loaning/loan_desk.html"
    permission_required = "loaning.view_loan"

    def get(self, request, *args, **kwargs):
        """Render the loan desk."""
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        """Process loan desk actions."""
        action = request.POST.get("action")
        if action == "create_customer":
            return self.create_customer()
        if action == "checkout":
            return self.checkout()
        if action == "return":
            return self.return_loan()
        messages.error(request, _("Unknown loan desk action."))
        return redirect("loaning:loan-desk")

    def get_context_data(self, **kwargs):
        """Build loan desk context."""
        customer_q = self.request.GET.get("customer_q", "").strip()
        book_q = self.request.GET.get("book_q", "").strip()
        selected_customer = self.get_selected_customer()
        selected_entry_number = self.get_selected_entry_number()
        customer_results = list(_customer_search(customer_q))
        entry_number_results = list(_entry_number_search(book_q))
        for entry_number in entry_number_results:
            entry_number.available_copies = max((entry_number.copies or 0) - entry_number.active_loan_count, 0)
        active_loans = Loan.objects.filter(status=Loan.STATUS_ACTIVE).select_related("customer", "entry_number")
        history_loans = Loan.objects.none()
        if selected_customer:
            active_loans = active_loans.filter(customer=selected_customer)
            history_loans = selected_customer.loan_set.exclude(status=Loan.STATUS_ACTIVE).select_related(
                "entry_number", "entry_number__book_entry"
            )[:25]
        if selected_entry_number:
            active_loans = active_loans.filter(entry_number=selected_entry_number)
            history_loans = selected_entry_number.loan_set.exclude(status=Loan.STATUS_ACTIVE).select_related(
                "customer", "entry_number__book_entry"
            )[:25]
        context = {
            "customer_q": customer_q,
            "book_q": book_q,
            "customer_results": customer_results,
            "entry_number_results": entry_number_results,
            "selected_customer": selected_customer,
            "selected_entry_number": selected_entry_number,
            "customer_form": kwargs.get("customer_form", CustomerForm()),
            "checkout_form": self.get_checkout_form(selected_customer, selected_entry_number),
            "return_form": LoanReturnForm(),
            "active_loans": active_loans,
            "history_loans": history_loans,
        }
        context.update(kwargs)
        return context

    def get_selected_customer(self):
        """Return selected customer, if any."""
        customer_id = self.request.GET.get("customer") or self.request.POST.get("customer_id")
        if not customer_id:
            return None
        return _annotate_customer(get_object_or_404(Customer, pk=customer_id))

    def get_selected_entry_number(self):
        """Return selected entry number, if any."""
        entry_number_id = self.request.GET.get("entry") or self.request.POST.get("entry_number_id")
        if not entry_number_id:
            return None
        return _annotate_entry_number(
            get_object_or_404(EntryNumber.objects.select_related("book_entry"), pk=entry_number_id)
        )

    def get_checkout_form(self, selected_customer, selected_entry_number):
        """Return an initialized checkout form when both sides are selected."""
        if not selected_customer or not selected_entry_number:
            return None
        return LoanCheckoutForm(
            initial={
                "customer_id": selected_customer.pk,
                "entry_number_id": selected_entry_number.pk,
                "start": datetime.date.today(),
                "expected_end": datetime.date.today() + datetime.timedelta(days=60),
            }
        ).as_bootstrap()

    def create_customer(self):
        """Create a customer inline from the loan desk."""
        if not self.request.user.has_perm("loaning.add_customer"):
            raise PermissionDenied
        form = CustomerForm(self.request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(self.request, _("Customer created successfully."))
            return redirect(f"{reverse_lazy('loaning:loan-desk')}?customer={customer.pk}")
        return self.render_to_response(self.get_context_data(customer_form=form))

    def checkout(self):
        """Create a loan from the selected customer and entry number."""
        if not self.request.user.has_perm("loaning.add_loan"):
            raise PermissionDenied
        form = LoanCheckoutForm(self.request.POST)
        selected_customer = self.get_selected_customer()
        selected_entry_number = self.get_selected_entry_number()
        if form.is_valid():
            if Loan.objects.filter(
                customer_id=form.cleaned_data["customer_id"],
                entry_number_id=form.cleaned_data["entry_number_id"],
                status=Loan.STATUS_ACTIVE,
            ).exists():
                messages.warning(self.request, _("This customer already has an active loan for this entry number."))
            if selected_customer and selected_customer.overdue_loan_count:
                messages.warning(self.request, _("This customer has overdue active loans."))
            loan = form.save()
            messages.success(self.request, _("Loan created successfully."))
            return redirect("loaning:loan-detail", pk=loan.pk)
        return self.render_to_response(
            self.get_context_data(
                checkout_form=form,
                selected_customer=selected_customer,
                selected_entry_number=selected_entry_number,
            )
        )

    def return_loan(self):
        """Return an active loan from the loan desk."""
        if not self.request.user.has_perm("loaning.change_loan"):
            raise PermissionDenied
        loan = get_object_or_404(Loan, pk=self.request.POST.get("loan_id"), status=Loan.STATUS_ACTIVE)
        form = LoanReturnForm(self.request.POST, loan=loan)
        if form.is_valid():
            form.save()
            messages.success(self.request, _("Loan returned successfully."))
            return redirect("loaning:loan-desk")
        messages.error(self.request, _("Could not return the loan."))
        return self.render_to_response(self.get_context_data(return_form=form))


class LoanDetailView(PermissionRequiredMixin, DetailView):
    """Loan detail and exception workflow."""

    model = Loan
    permission_required = "loaning.view_loan"
    template_name = "loaning/loan_detail.html"

    def get_context_data(self, **kwargs):
        """Add exception form."""
        context = super().get_context_data(**kwargs)
        context["exception_form"] = kwargs.get("exception_form", LoanExceptionForm(loan=self.object))
        context["available_copies"] = available_copies(self.object.entry_number)
        return context

    def post(self, request, *args, **kwargs):
        """Mark a loan lost or cancelled."""
        self.object = self.get_object()
        if not request.user.has_perm("loaning.change_loan"):
            raise PermissionDenied
        if self.object.status != Loan.STATUS_ACTIVE:
            messages.error(request, _("Only active loans can be changed."))
            return redirect("loaning:loan-detail", pk=self.object.pk)
        action = request.POST.get("action")
        if action == "lost" and not request.user.has_perm("books.change_entrynumber"):
            raise PermissionDenied
        form = LoanExceptionForm(request.POST, loan=self.object)
        if form.is_valid():
            if action == "returned":
                form.save()
                messages.success(request, _("Loan returned."))
            elif action == "lost":
                form.save_lost()
                messages.success(request, _("Loan marked lost and copy count reduced."))
            elif action == "cancelled":
                form.save_cancelled()
                messages.success(request, _("Loan cancelled."))
            else:
                messages.error(request, _("Unknown loan action."))
            return redirect("loaning:loan-detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(exception_form=form))
