from django.db import models, transaction # Ensure transaction is imported
from django.conf import settings # For linking to the User model
from organization.models import BusinessUnit # Customers are typically associated with a Company or Group
from decimal import Decimal # Ensure Decimal is imported

class Customer(models.Model):
    company_owner = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        limit_choices_to={'unit_type__in': [BusinessUnit.UnitType.COMPANY, BusinessUnit.UnitType.GROUP]},
        related_name='customers',
        help_text="The main organizational unit (Tenant Group or specific Company) this customer belongs to."
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    can_purchase_on_credit = models.BooleanField(default=False)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00')) # Use Decimal for default
    current_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), # Use Decimal for default
        help_text="Automatically updated. Positive: Customer owes money. Negative: Customer has credit."
    )

    tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="Customer's Tax ID / NTN")
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"{self.name} (Owner: {self.company_owner.name})"


class CustomerLedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        SALE_INVOICE = 'INVOICE', 'Sale Invoice (Credit)'
        PAYMENT_RECEIVED = 'PAYMENT', 'Payment Received'
        CREDIT_NOTE = 'CREDIT_NOTE', 'Credit Note (Return/Refund)'
        DEBIT_NOTE = 'DEBIT_NOTE', 'Debit Note (Other Charges)'
        OPENING_BALANCE = 'OPENING', 'Opening Balance'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ledger_entries')
    entry_date = models.DateTimeField(auto_now_add=True)
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    sale = models.ForeignKey('sales.Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_ledger_entries_from_sale')
    description = models.CharField(max_length=255, blank=True, null=True)
    debit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00')) # Use Decimal for default
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00')) # Use Decimal for default
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_customer_ledger_entries')

    _original_debit_amount = Decimal('0.00')
    _original_credit_amount = Decimal('0.00')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk: # If loading an existing instance
            self._original_debit_amount = self.debit_amount if self.debit_amount is not None else Decimal('0.00')
            self._original_credit_amount = self.credit_amount if self.credit_amount is not None else Decimal('0.00')
        # For new instances, _original_debit_amount and _original_credit_amount
        # will retain their class-level Decimal('0.00') values.
            
    class Meta:
        ordering = ['-entry_date', '-id']
        verbose_name = "Customer Ledger Entry"
        verbose_name_plural = "Customer Ledger Entries"

    def __str__(self):
        return f"{self.get_entry_type_display()} for {self.customer.name} on {self.entry_date.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            is_new = not self.pk

            # Ensure current values are Decimal, defaulting to Decimal('0.00') if None
            current_debit = self.debit_amount if self.debit_amount is not None else Decimal('0.00')
            current_credit = self.credit_amount if self.credit_amount is not None else Decimal('0.00')
            
            # _original_debit_amount and _original_credit_amount are already Decimal
            # due to class attribute definition and __init__ logic.

            balance_change = Decimal('0.00')
            if is_new:
                balance_change = current_debit - current_credit
            else: # It's an update to an existing entry
                debit_diff = current_debit - self._original_debit_amount
                credit_diff = current_credit - self._original_credit_amount
                balance_change = debit_diff - credit_diff
            
            # Before saving the entry, ensure self.debit_amount and self.credit_amount are actual Decimal values
            self.debit_amount = current_debit
            self.credit_amount = current_credit

            super().save(*args, **kwargs) # Save the ledger entry itself

            if balance_change != Decimal('0.00'):
                customer_to_update = Customer.objects.select_for_update().get(pk=self.customer.pk)
                # Ensure customer's current balance is also treated as Decimal before arithmetic
                customer_current_balance = customer_to_update.current_balance if customer_to_update.current_balance is not None else Decimal('0.00')
                customer_to_update.current_balance = customer_current_balance + balance_change
                customer_to_update.save(update_fields=['current_balance'])
            
            # Update original amounts tracker AFTER the save and potential update
            self._original_debit_amount = current_debit
            self._original_credit_amount = current_credit
    
    def delete(self, *args, **kwargs):
        with transaction.atomic():
            # Ensure values are Decimal before calculation
            entry_debit = self.debit_amount if self.debit_amount is not None else Decimal('0.00')
            entry_credit = self.credit_amount if self.credit_amount is not None else Decimal('0.00')
            balance_reversal = entry_credit - entry_debit

            super().delete(*args, **kwargs)

            if balance_reversal != Decimal('0.00'):
                customer_to_update = Customer.objects.select_for_update().get(pk=self.customer.pk)
                customer_current_balance = customer_to_update.current_balance if customer_to_update.current_balance is not None else Decimal('0.00')
                customer_to_update.current_balance = customer_current_balance + balance_reversal
                customer_to_update.save(update_fields=['current_balance'])
