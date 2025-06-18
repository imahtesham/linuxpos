from django.contrib import admin
from .models import Sale, SaleItem # Make sure Customer model is NOT imported here if not directly used

class SaleItemInline(admin.TabularInline): # Or StackedInline for a different layout
    model = SaleItem
    extra = 1 # Number of empty forms to display for new Sales
    autocomplete_fields = ['product']
    readonly_fields = ('total_price',) # total_price is calculated in the model's save method

    # You might want to add fields like 'unit_price_at_sale' to be editable,
    # or automatically populate it from ProductPrice based on branch/price_list
    # when a product is selected. This requires more advanced JavaScript or custom form logic.
    # For now, it needs to be manually entered by the admin user.

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'sale_number', 
        'branch', 
        'customer', # UPDATED from 'customer_name'
        'sale_date', 
        'status', 
        'grand_total', 
        'payment_type', 
        'processed_by', 
        'stock_deducted'
    )
    list_filter = (
        'branch', 
        'status', 
        'payment_type', 
        'sale_date', 
        'processed_by', 
        'customer' # ADDED customer to filter
    )
    search_fields = (
        'sale_number', 
        'customer__name', # UPDATED to search by related customer's name
        'branch__name', 
        'processed_by__username'
    )
    # Fields that are automatically set or calculated
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'sub_total', 
        'grand_total', 
        'change_due', 
        'stock_deducted'
    ) 
    autocomplete_fields = [
        'branch', 
        'processed_by', 
        'customer' # ADDED customer for autocomplete
    ] 
    date_hierarchy = 'sale_date'
    inlines = [SaleItemInline] # Allows adding SaleItems directly when creating/editing a Sale
    list_per_page = 20

    fieldsets = (
        (None, {
            'fields': ('sale_number', ('branch', 'customer'), ('sale_date', 'status'), 'processed_by') # UPDATED customer_name to customer
        }),
        ('Financials', {
            'fields': ('discount_amount', 'tax_amount', 'sub_total', 'grand_total') 
        }),
        ('Payment', {
            'fields': (('payment_type', 'amount_paid'), 'change_due')
        }),
        ('Notes & System', {
            'fields': ('notes', 'stock_deducted'),
            'classes': ('collapse',)
        }),
        ('Timestamps', { # Explicitly showing the audit timestamps
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',) 
        }),
    )
    
    # IMPORTANT: Logic to deduct stock on Sale completion is in the Sale model's save() method.
    # Logic to create CustomerLedgerEntry for 'ON_ACCOUNT' sales is also in Sale model's save().

    def get_queryset(self, request):
        # Optimize query by prefetching related objects
        return super().get_queryset(request).select_related('branch', 'processed_by', 'customer') # ADDED customer

# SaleItem can also be registered separately if needed for direct access,
# but it's primarily managed via the Sale inline.
# @admin.register(SaleItem)
# class SaleItemAdmin(admin.ModelAdmin):
#     list_display = ('sale', 'product', 'quantity', 'unit_price_at_sale', 'total_price')
#     list_filter = ('sale__branch', 'product__category')
#     search_fields = ('sale__sale_number', 'product__name')
#     readonly_fields = ('total_price',)
#     autocomplete_fields = ['sale', 'product']
