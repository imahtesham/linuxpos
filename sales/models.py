from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from organization.models import BusinessUnit
from products.models import Product
from inventory.models import InventoryStock
from customers.models import Customer, CustomerLedgerEntry # <<< IMPORTED CUSTOMER MODEL
from decimal import Decimal

class Sale(models.Model):
    class SaleStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REFUNDED = 'REFUNDED', 'Refunded'

    class PaymentType(models.TextChoices):
        CASH = 'CASH', 'Cash'
        CARD = 'CARD', 'Card'
        MOBILE_WALLET = 'MOBILE', 'Mobile Wallet'
        BANK_TRANSFER = 'BANK', 'Bank Transfer'
        ON_ACCOUNT = 'ACCOUNT', 'On Account (Credit)' # For sales to customers on credit
        VOUCHER = 'VOUCHER', 'Voucher'
        OTHER = 'OTHER', 'Other'

    branch = models.ForeignKey(
        BusinessUnit,
        on_delete=models.PROTECT,
        limit_choices_to={'unit_type': BusinessUnit.UnitType.BRANCH},
        related_name='sales'
    )
    # Replaced customer_name CharField with ForeignKey to Customer
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.SET_NULL, # If customer is deleted, keep sale but unlink customer
        null=True, blank=True,     # Sale can be made to a walk-in customer (no specific customer selected)
        related_name='sales_as_customer' # Changed related_name to avoid clash with CustomerLedgerEntry
    )

    sale_number = models.CharField(max_length=50, unique=True, help_text="Unique sale identifier/invoice number")
    sale_date = models.DateTimeField(default=timezone.now, help_text="Date and time the sale transaction occurred")
    status = models.CharField(max_length=10, choices=SaleStatus.choices, default=SaleStatus.PENDING)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_type = models.CharField(max_length=10, choices=PaymentType.choices, blank=True, null=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    change_due = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_sales'
    )
    notes = models.TextField(blank=True, null=True)
    stock_deducted = models.BooleanField(default=False, help_text="Indicates if stock was deducted for this sale.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    _original_status = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status

    class Meta:
        ordering = ['-sale_date', '-created_at']
        verbose_name = "Sale Transaction"
        verbose_name_plural = "Sale Transactions"

    def __str__(self):
        customer_info = f" for {self.customer.name}" if self.customer else ""
        return f"Sale #{self.sale_number} at {self.branch.name}{customer_info} on {self.sale_date.strftime('%Y-%m-%d %H:%M')}"

    def update_calculated_fields(self):
        current_sub_total = Decimal('0.00')
        if self.pk:
            for item in self.items.all():
                current_sub_total += item.total_price
        self.sub_total = current_sub_total
        self.grand_total = (self.sub_total - self.discount_amount) + self.tax_amount

    def _perform_stock_deduction(self):
        if not self.pk: return
        for item in self.items.all():
            if not item.product.is_inventory_tracked: continue
            try:
                stock_item = InventoryStock.objects.get(branch=self.branch, product=item.product)
                if stock_item.quantity < item.quantity:
                    raise ValidationError(
                        f"Insufficient stock for {item.product.name} at {self.branch.name}. "
                        f"Required: {item.quantity}, Available: {stock_item.quantity}."
                    )
                stock_item.quantity -= item.quantity
                stock_item.save()
            except InventoryStock.DoesNotExist:
                if item.quantity > 0:
                    raise ValidationError(
                        f"No stock record for {item.product.name} at {self.branch.name}. Cannot sell {item.quantity}."
                    )
        self.stock_deducted = True

    def _perform_stock_reversal(self):
        if not self.pk: return
        for item in self.items.all():
            if not item.product.is_inventory_tracked: continue
            stock_item, created = InventoryStock.objects.get_or_create(
                branch=self.branch, product=item.product, defaults={'quantity': Decimal('0.00')}
            )
            stock_item.quantity += item.quantity
            stock_item.save()
        self.stock_deducted = False

    def save(self, *args, **kwargs):
        self.update_calculated_fields()
        is_new = self._state.adding
        status_changed = self._original_status != self.status
        
        # Determine if stock operations should occur
        process_stock_now = False
        revert_stock_now = False

        if (is_new and self.status == self.SaleStatus.COMPLETED and not self.stock_deducted) or \
           (status_changed and self.status == self.SaleStatus.COMPLETED and not self.stock_deducted):
            process_stock_now = True
        elif status_changed and self._original_status == self.SaleStatus.COMPLETED and self.stock_deducted:
            revert_stock_now = True

        if process_stock_now:
            with transaction.atomic():
                self._perform_stock_deduction() # This might raise ValidationError
                super().save(*args, **kwargs) # Save Sale only if stock deduction succeeds
                # After successful save, if it was a credit sale, create ledger entry
                if self.payment_type == self.PaymentType.ON_ACCOUNT and self.customer:
                    CustomerLedgerEntry.objects.create(
                        customer=self.customer,
                        entry_type=CustomerLedgerEntry.EntryType.SALE_INVOICE,
                        sale=self,
                        description=f"Sale Invoice #{self.sale_number}",
                        debit_amount=self.grand_total,
                        created_by=self.processed_by # Or request.user if available from context
                    )
        elif revert_stock_now:
            with transaction.atomic():
                self._perform_stock_reversal()
                super().save(*args, **kwargs)
                # If reverting a credit sale, a Credit Note ledger entry might be needed.
                # This could be triggered by a Sale Return process rather than just changing status.
                # For now, just reverting stock. A separate "Refund" process would create the Credit Note.
        else:
            super().save(*args, **kwargs)

        self._original_status = self.status

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price_at_sale = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount_item = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} @ {self.unit_price_at_sale}"

    def save(self, *args, **kwargs):
        self.total_price = (self.quantity * self.unit_price_at_sale) - self.discount_amount_item
        super().save(*args, **kwargs)
        if self.sale:
            self.sale.update_calculated_fields()
            self.sale.save(update_fields=['sub_total', 'grand_total'])
