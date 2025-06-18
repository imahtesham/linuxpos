from django.db import models
from django.conf import settings # For linking to the User model
from organization.models import BusinessUnit # Customers are typically associated with a Company or Group

class Customer(models.Model):
    company_owner = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        # Allow customers to be owned by either a top-level Group (tenant) or a Company within that Group
        limit_choices_to={'unit_type__in': [BusinessUnit.UnitType.COMPANY, BusinessUnit.UnitType.GROUP]},
        related_name='customers',
        help_text="The main organizational unit (Tenant Group or specific Company) this customer belongs to."
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    can_purchase_on_credit = models.BooleanField(default=False)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    current_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Automatically updated. Positive: Customer owes money. Negative: Customer has credit."
    )

    tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="Customer's Tax ID / NTN")
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Consider making name or phone unique within the company_owner scope if needed
        # unique_together = ('company_owner', 'phone_number') 
        ordering = ['name']
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"{self.name} (Owner: {self.company_owner.name})"

class CustomerLedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        SALE_INVOICE = 'INVOICE', 'Sale Invoice (Credit)'
        PAYMENT_RECEIVED = 'PAYMENT', 'Payment Received'
        CREDIT_NOTE = 'CREDIT_NOTE', 'Credit Note (Return/Refund)' # e.g. from Sales Return
        DEBIT_NOTE = 'DEBIT_NOTE', 'Debit Note (Other Charges)' # e.g. service fee
        OPENING_BALANCE = 'OPENING', 'Opening Balance'
        # JOURNAL_ADJUSTMENT = 'JOURNAL', 'Journal Adjustment' # For manual corrections

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ledger_entries')
    entry_date = models.DateTimeField(auto_now_add=True) # When the ledger event occurred/was recorded
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    
    # Link to the source document if applicable
    # Important: Ensure sales app is listed before customers in INSTALLED_APPS if using string reference like this
    # or import Sale directly. For now, let's assume direct import or correct app order.
    sale = models.ForeignKey('sales.Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_ledger_entries_from_sale') 
    # payment_receipt = models.ForeignKey('payments.PaymentReceipt', on_delete=models.SET_NULL, null=True, blank=True) # If you have a separate Payment model

    description = models.CharField(max_length=255, blank=True, null=True)
    debit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Increases amount customer owes")
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Decreases amount customer owes (e.g., payment)")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_customer_ledger_entries')
    # created_at is implicit due to entry_date with auto_now_add=True

    class Meta:
        ordering = ['-entry_date', '-id']
        verbose_name = "Customer Ledger Entry"
        verbose_name_plural = "Customer Ledger Entries"

    def __str__(self):
        return f"{self.get_entry_type_display()} for {self.customer.name} on {self.entry_date.strftime('%Y-%m-%d')}"

    # Logic to update Customer.current_balance will be added to save() method or via signals.
