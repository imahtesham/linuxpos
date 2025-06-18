from django.db import models, transaction # Import transaction
from django.core.exceptions import ValidationError
from organization.models import BusinessUnit
from products.models import Product, Supplier
from django.contrib.auth.models import User

# ... (InventoryStock model remains the same) ...
class InventoryStock(models.Model):
    branch = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        limit_choices_to={'unit_type': BusinessUnit.UnitType.BRANCH},
        related_name='stock_items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_records')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('branch', 'product')
        verbose_name = "Inventory Stock Level"
        verbose_name_plural = "Inventory Stock Levels"
        ordering = ['branch', 'product']

    def __str__(self):
        return f"{self.product.name} at {self.branch.name}: {self.quantity}"

    def clean(self):
        if self.product and not self.product.is_inventory_tracked:
            raise ValidationError(f"Product '{self.product.name}' is not marked for inventory tracking.")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class GoodsReceiveNote(models.Model):
    class GRNStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    branch = models.ForeignKey(
        BusinessUnit,
        on_delete=models.PROTECT,
        limit_choices_to={'unit_type': BusinessUnit.UnitType.BRANCH},
        related_name='grns'
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='grns')
    grn_number = models.CharField(max_length=50, unique=True, help_text="Unique GRN identifier, can be auto-generated")
    supplier_invoice_number = models.CharField(max_length=50, blank=True, null=True)
    received_date = models.DateField()
    status = models.CharField(max_length=10, choices=GRNStatus.choices, default=GRNStatus.PENDING)
    notes = models.TextField(blank=True, null=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='grns_received')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Keep track of the old status to detect changes
    _original_status = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status

    class Meta:
        ordering = ['-received_date', '-created_at']
        verbose_name = "Goods Receive Note (GRN)"
        verbose_name_plural = "Goods Receive Notes (GRNs)"

    def __str__(self):
        return f"GRN #{self.grn_number} for {self.branch.name} from {self.supplier.name}"

    def process_stock_update(self):
        """
        Updates InventoryStock for all items in this GRN.
        This should only be called when GRN status is COMPLETED.
        """
        if self.status != self.GRNStatus.COMPLETED:
            # Or raise an error, or just log. For now, we silently return.
            return

        for item in self.items.all():
            if not item.product.is_inventory_tracked:
                continue # Skip non-inventory items

            stock_item, created = InventoryStock.objects.get_or_create(
                branch=self.branch,
                product=item.product,
                defaults={'quantity': 0} # Default quantity if new stock item
            )
            stock_item.quantity += item.quantity_received
            stock_item.save()
            
            # Optional: Update product's last cost price if desired
            # item.product.cost_price = item.cost_price_per_unit
            # item.product.save(update_fields=['cost_price'])

    def revert_stock_update(self):
        """
        Reverts InventoryStock updates if a COMPLETED GRN is changed to another status (e.g., CANCELLED).
        This logic needs to be robust, considering if stock has already been sold.
        For simplicity, this example directly subtracts. More complex scenarios might prevent this
        or require adjustments.
        """
        # This is a simplified revert. Real-world might be more complex.
        # E.g., what if stock from this GRN was already sold?
        for item in self.items.all():
            if not item.product.is_inventory_tracked:
                continue

            try:
                stock_item = InventoryStock.objects.get(
                    branch=self.branch,
                    product=item.product
                )
                # Be cautious with allowing quantity to go negative if not intended
                stock_item.quantity -= item.quantity_received
                stock_item.save()
            except InventoryStock.DoesNotExist:
                # This shouldn't happen if it was previously completed, but handle defensively
                pass


    def save(self, *args, **kwargs):
        # Atomically update GRN and stock to prevent partial updates
        with transaction.atomic():
            is_new = self._state.adding # Check if this is a new GRN instance
            
            # Call Django's validation before saving
            # self.full_clean() # Be careful with calling full_clean in save, it can be tricky with admin
            
            super().save(*args, **kwargs) # Save the GRN itself first

            status_changed = self._original_status != self.status

            if status_changed:
                if self.status == self.GRNStatus.COMPLETED:
                    self.process_stock_update()
                elif self._original_status == self.GRNStatus.COMPLETED and self.status != self.GRNStatus.COMPLETED:
                    # GRN was completed, but now status changed (e.g., to PENDING or CANCELLED)
                    # We might want to revert the stock. This is complex.
                    # For now, let's assume we want to revert if it's no longer COMPLETED.
                    self.revert_stock_update() 
                    # Consider logging or preventing this if stock might have been consumed.

            # If it's a new GRN and status is set to COMPLETED directly upon creation
            elif is_new and self.status == self.GRNStatus.COMPLETED:
                self.process_stock_update()

            # Update the original status tracker after save
            self._original_status = self.status

# ... (GRNItem model remains the same) ...
class GRNItem(models.Model):
    grn = models.ForeignKey(GoodsReceiveNote, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost price for this specific shipment")

    def __str__(self):
        return f"{self.quantity_received} x {self.product.name} @ {self.cost_price_per_unit}"

    def clean(self):
        if self.product and not self.product.is_inventory_tracked:
            raise ValidationError(f"Product '{self.product.name}' cannot be added to GRN as it is not inventory-tracked.")
        if self.quantity_received <= 0:
            raise ValidationError("Quantity received must be greater than zero.")
        if self.cost_price_per_unit < 0:
            raise ValidationError("Cost price cannot be negative.")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
