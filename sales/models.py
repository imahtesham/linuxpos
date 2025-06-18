# Ensure all necessary imports are at the top of sales/models.py
from django.db import models # <<< THIS LINE IS CRUCIAL

# ... then your other imports ...
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from organization.models import BusinessUnit
from products.models import Product
from inventory.models import InventoryStock
from decimal import Decimal
from django.db import models, transaction # Ensure this is also there if you're using transaction.atomic()


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
        ON_ACCOUNT = 'ACCOUNT', 'On Account (Credit)'
        VOUCHER = 'VOUCHER', 'Voucher'
        OTHER = 'OTHER', 'Other'

    branch = models.ForeignKey(
        BusinessUnit,
        on_delete=models.PROTECT,
        limit_choices_to={'unit_type': BusinessUnit.UnitType.BRANCH},
        related_name='sales'
    )
    customer_name = models.CharField(max_length=255, blank=True, null=True, help_text="Temporary, replace with FK to Customer model")
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
        return f"Sale #{self.sale_number} at {self.branch.name} on {self.sale_date.strftime('%Y-%m-%d %H:%M')}"

    def update_calculated_fields(self):
        current_sub_total = Decimal('0.00')
        if self.pk:
            for item in self.items.all():
                current_sub_total += item.total_price
        self.sub_total = current_sub_total
        self.grand_total = (self.sub_total - self.discount_amount) + self.tax_amount

    def _perform_stock_deduction(self):
        """Deducts stock for all items in this sale. Raises ValidationError on insufficient stock."""
        if not self.pk: # Should not happen if called correctly
            return

        for item in self.items.all():
            if not item.product.is_inventory_tracked:
                continue

            try:
                stock_item = InventoryStock.objects.get(
                    branch=self.branch,
                    product=item.product
                )
                if stock_item.quantity < item.quantity:
                    # Not enough stock!
                    # Depending on business rules, you might:
                    # 1. Raise ValidationError (prevents sale completion) - chosen here
                    # 2. Allow negative stock (if a setting permits)
                    # 3. Log a warning and proceed
                    raise ValidationError(
                        f"Insufficient stock for {item.product.name} at {self.branch.name}. "
                        f"Required: {item.quantity}, Available: {stock_item.quantity}."
                    )
                stock_item.quantity -= item.quantity
                stock_item.save()
            except InventoryStock.DoesNotExist:
                # Product has no stock record at this branch, meaning stock is effectively 0.
                # If quantity sold is > 0, this is an insufficient stock situation.
                if item.quantity > 0:
                    raise ValidationError(
                        f"No stock record (implies 0 stock) for {item.product.name} at {self.branch.name}. "
                        f"Cannot sell {item.quantity}."
                    )
        self.stock_deducted = True

    def _perform_stock_reversal(self):
        """Reverts stock deduction for all items in this sale."""
        if not self.pk:
            return

        for item in self.items.all():
            if not item.product.is_inventory_tracked:
                continue
            
            # Use get_or_create in case a stock record was somehow deleted after sale
            stock_item, created = InventoryStock.objects.get_or_create(
                branch=self.branch,
                product=item.product,
                defaults={'quantity': Decimal('0.00')} 
            )
            stock_item.quantity += item.quantity
            stock_item.save()
        self.stock_deducted = False

    def save(self, *args, **kwargs):
        self.update_calculated_fields() # Always calculate totals first

        # Determine if this save operation should trigger stock changes
        is_new = self._state.adding
        status_changed = self._original_status != self.status
        
        # --- Stock Deduction Logic ---
        if (is_new and self.status == self.SaleStatus.COMPLETED and not self.stock_deducted) or \
           (status_changed and self.status == self.SaleStatus.COMPLETED and not self.stock_deducted):
            # Using transaction.atomic to ensure sale save and all stock updates are one operation
            with transaction.atomic():
                self._perform_stock_deduction() # This might raise ValidationError
                # If _perform_stock_deduction succeeds, then save the Sale itself
                super().save(*args, **kwargs) 
        # --- Stock Reversal Logic ---
        elif status_changed and self._original_status == self.SaleStatus.COMPLETED and self.stock_deducted:
            # If status changed FROM completed TO something else, and stock was previously deducted
            with transaction.atomic():
                self._perform_stock_reversal()
                super().save(*args, **kwargs)
        else:
            # Default save if no stock logic is triggered or if it's just an update to other fields
            super().save(*args, **kwargs)

        self._original_status = self.status # Update after save

# ... (SaleItem model remains the same) ...
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
