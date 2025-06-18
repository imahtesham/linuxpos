from django.db import models
from organization.models import BusinessUnit # To link products/suppliers to a company level

# It's good practice to associate master data like Suppliers and Product definitions
# with a specific Company within your BusinessUnit hierarchy.
# This assumes a "Company" level BusinessUnit is where product catalogs are managed.

class Supplier(models.Model):
    company_owner = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        limit_choices_to={'unit_type': BusinessUnit.UnitType.COMPANY}, # Supplier belongs to a Company
        related_name='suppliers',
        help_text="The company in your organization that manages this supplier relationship."
    )
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company_owner', 'name') # Supplier name should be unique within a company
        ordering = ['name']

    def __str__(self):
        return self.name

class Category(models.Model):
    company_owner = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        limit_choices_to={'unit_type': BusinessUnit.UnitType.COMPANY},
        related_name='product_categories',
        help_text="The company in your organization that defines this category."
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE, # Or models.SET_NULL if you want subcategories to remain if parent is deleted
        null=True,
        blank=True,
        related_name='subcategories'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ('company_owner', 'name', 'parent') # Category name unique within its parent & company
        ordering = ['name']

    def __str__(self):
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return " / ".join(path)

class Product(models.Model):
    class ProductType(models.TextChoices):
        FINISHED_GOOD = 'FINISHED', 'Finished Good' # Purchased and sold as is, or manufactured
        RAW_MATERIAL = 'RAW', 'Raw Material'     # Used in recipes, not sold directly
        SERVICE = 'SERVICE', 'Service'           # Non-inventory item like a delivery charge

    company_owner = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        limit_choices_to={'unit_type': BusinessUnit.UnitType.COMPANY},
        related_name='products',
        help_text="The company in your organization that owns this product definition."
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    sku = models.CharField(max_length=100, blank=True, null=True, help_text="Stock Keeping Unit")
    barcode = models.CharField(max_length=100, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    product_type = models.CharField(max_length=10, choices=ProductType.choices, default=ProductType.FINISHED_GOOD)
    is_inventory_tracked = models.BooleanField(default=True, help_text="If false, stock levels are not managed for this item (e.g., services).")
    
    # Default Cost Price - this might be an average or last cost. Actual GRN cost is more specific.
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Shelf life - for batch tracking later
    shelf_life_days = models.IntegerField(default=0, help_text="Shelf life in days. 0 means not applicable.")

    # Tax related fields - can be simple or complex depending on needs
    # For now, let's assume tax is handled at POS/Sale time based on branch location.
    # We can add a tax_rate ForeignKey here if products have specific tax rates.

    # Discount settings
    allow_discount = models.BooleanField(default=True)
    max_discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, 
        help_text="Maximum discount allowed for this item in percentage (e.g., 10.00 for 10%)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # A product SKU should be unique within the company that owns it
        unique_together = ('company_owner', 'sku') 
        # A product name could also be unique, or name+category
        # unique_together = ('company_owner', 'name', 'category')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})" if self.sku else self.name


class PriceList(models.Model):
    company_owner = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        limit_choices_to={'unit_type': BusinessUnit.UnitType.COMPANY},
        related_name='price_lists'
    )
    name = models.CharField(max_length=100, help_text="e.g., Retail, Wholesale, Take Away, Dine-In")
    is_default = models.BooleanField(default=False, help_text="Is this the default price list for new products/branches?")
    # You could add start_date, end_date for promotional price lists

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('company_owner', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name

class ProductPrice(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name='product_prices')
    # Price can be branch-specific OR company-wide for a given price list.
    # For maximum flexibility, let's allow branch-specific overrides.
    # If branch is NULL, it's a company-level price for that price list.
    branch = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        limit_choices_to={'unit_type': BusinessUnit.UnitType.BRANCH},
        related_name='branch_product_prices',
        null=True, blank=True, # If null, this price applies to all branches of the product's company_owner for this price_list
        help_text="Specific branch for this price. If blank, applies to all branches under the product's company owner."
    )
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Tax settings for this specific price (can be inclusive/exclusive)
    # For simplicity now, let's assume global tax settings apply.
    # tax_inclusive = models.BooleanField(default=False) 

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # A product should have only one price per price list per branch (or one company-wide price if branch is null)
        unique_together = ('product', 'price_list', 'branch')
        ordering = ['price_list', 'branch', 'product']

    def __str__(self):
        branch_name = f" ({self.branch.name})" if self.branch else " (Company-wide)"
        return f"{self.product.name} - {self.price_list.name}{branch_name}: {self.sale_price}"
