from django.db import models
from django.core.exceptions import ValidationError
from organization.models import BusinessUnit
from products.models import Product, Supplier
from django.contrib.auth.models import User # For received_by field

class InventoryStock(models.Model):
    branch = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        limit_choices_to={'unit_type': BusinessUnit.UnitType.BRANCH},
        related_name='stock_items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_records')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Use Decimal for items sold by weight/volume
    # If all products are whole units, you could use models.IntegerField(default=0)

    # For advanced batch/expiry tracking (FEFO - First Expired, First Out) - can be added later
    # batch_number = models.CharField(max_length=100, blank=True, null=True)
    # expiry_date = models.DateField(blank=True, null=True)
    # last_cost_price_of_this_batch = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('branch', 'product') # Each product has one stock record per branch
        # If doing batch tracking, unique_together would be ('branch', 'product', 'batch_number')
        verbose_name = "Inventory Stock Level"
        verbose_name_plural = "Inventory Stock Levels"
        ordering = ['branch', 'product']

    def __str__(self):
        return f"{self.product.name} at {self.branch.name}: {self.quantity}"

    def clean(self):
        # Ensure product is inventory tracked
        if self.product and not self.product.is_inventory_tracked:
            raise ValidationError(f"Product '{self.product.name}' is not marked for inventory tracking.")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean() # Call full_clean before saving
        super().save(*args, **kwargs)


class GoodsReceiveNote(models.Model):
    class GRNStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    branch = models.ForeignKey(
        BusinessUnit,
        on_delete=models.PROTECT, # Don't delete GRNs if branch is deleted, consider behavior
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

    class Meta:
        ordering = ['-received_date', '-created_at']
        verbose_name = "Goods Receive Note (GRN)"
        verbose_name_plural = "Goods Receive Notes (GRNs)"

    def __str__(self):
        return f"GRN #{self.grn_number} for {self.branch.name} from {self.supplier.name}"

    # We'll add a method later to process the GRN and update stock levels
    # when its status changes to 'COMPLETED'.


class GRNItem(models.Model):
    grn = models.ForeignKey(GoodsReceiveNote, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT) # Protect product from deletion if in a GRN
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost price for this specific shipment")
    
    # For batch/expiry - if implemented
    # batch_number = models.CharField(max_length=100, blank=True, null=True)
    # expiry_date = models.DateField(blank=True, null=True)

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
