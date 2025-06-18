from django.contrib import admin
from .models import Supplier, Category, Product, PriceList, ProductPrice

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_owner', 'contact_person', 'email', 'phone_number', 'updated_at')
    list_filter = ('company_owner',)
    search_fields = ('name', 'contact_person', 'email', 'company_owner__name')
    # Consider making company_owner readonly on change or filtering its queryset based on logged-in user
    # For now, superuser will manage this.

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_owner', 'parent', 'description', 'updated_at')
    list_filter = ('company_owner', 'parent')
    search_fields = ('name', 'description', 'company_owner__name', 'parent__name')
    # For a better hierarchical display, you might later explore django-mptt or django-admin-sortable2

class ProductPriceInline(admin.TabularInline): # Or admin.StackedInline for a different layout
    model = ProductPrice
    extra = 1 # Number of empty forms to display
    # You might want to filter the 'price_list' and 'branch' fields here
    # based on the Product's company_owner if you get more advanced.
    autocomplete_fields = ['price_list', 'branch']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'sku', 'company_owner', 'category', 'product_type', 
        'cost_price', 'is_inventory_tracked', 'supplier', 'updated_at'
    )
    list_filter = ('company_owner', 'category', 'product_type', 'is_inventory_tracked', 'supplier')
    search_fields = ('name', 'sku', 'barcode', 'description', 'company_owner__name', 'category__name')
    list_editable = ('cost_price', 'is_inventory_tracked') # Use with caution
    autocomplete_fields = ['category', 'supplier', 'company_owner']
    
    fieldsets = (
        (None, {
            'fields': ('company_owner', 'name', 'description', 'category', 'supplier')
        }),
        ('Identification & Type', {
            'fields': ('sku', 'barcode', 'product_type', 'is_inventory_tracked')
        }),
        ('Pricing & Cost', {
            'fields': ('cost_price',) # Sale prices are handled by ProductPrice inline
        }),
        ('Settings', {
            'fields': ('allow_discount', 'max_discount_percentage', 'shelf_life_days')
        }),
    )
    inlines = [ProductPriceInline] # Allows adding/editing ProductPrices directly on the Product page

@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_owner', 'is_default', 'updated_at')
    list_filter = ('company_owner', 'is_default')
    search_fields = ('name', 'company_owner__name')

# ProductPrice can also be managed directly, though it's often handled via the Product inline
@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'price_list', 'branch', 'sale_price', 'updated_at')
    list_filter = ('price_list', 'branch', 'product__company_owner')
    search_fields = ('product__name', 'price_list__name', 'branch__name')
    autocomplete_fields = ['product', 'price_list', 'branch']
    # You might want to filter querysets for product, price_list, and branch
    # based on the company of the logged-in user if non-superusers manage this.
