from django.contrib import admin
from .models import Sale, SaleItem

class SaleItemInline(admin.TabularInline): # Or StackedInline for a different layout
    model = SaleItem
    extra = 1 # Number of empty forms to display for new Sales
    autocomplete_fields = ['product']
    readonly_fields = ('total_price',) # total_price is calculated in the model's save method

    # You might want to add fields like 'unit_price_at_sale' to be editable,
    # or automatically populate it from ProductPrice based on branch/price_list
    # when a product is selected. This requires more advanced JavaScript or custom form logic.
    # For now, it needs to be manually entered.

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'sale_number', 'branch', 'customer_name', 'sale_date', 'status', 
        'grand_total', 'payment_type', 'processed_by', 'stock_deducted'
    )
    list_filter = ('branch', 'status', 'payment_type', 'sale_date', 'processed_by')
    search_fields = ('sale_number', 'customer_name', 'branch__name', 'processed_by__username')
    readonly_fields = ('created_at', 'updated_at', 'sub_total', 'grand_total', 'change_due', 'stock_deducted') # Some fields are calculated or system-set
    autocomplete_fields = ['branch', 'processed_by'] # Add 'customer' when you have a Customer model
    date_hierarchy = 'sale_date'
    inlines = [SaleItemInline] # Allows adding SaleItems directly when creating/editing a Sale
    list_per_page = 20

    fieldsets = (
        (None, {
            'fields': ('sale_number', ('branch', 'customer_name'), ('sale_date', 'status'), 'processed_by')
        }),
        ('Financials', {
            # sub_total, grand_total are calculated. discount_amount, tax_amount are inputs that affect grand_total.
            'fields': ('discount_amount', 'tax_amount', 'sub_total', 'grand_total') 
        }),
        ('Payment', {
            'fields': (('payment_type', 'amount_paid'), 'change_due')
        }),
        ('Notes & System', {
            'fields': ('notes', 'stock_deducted'),
            'classes': ('collapse',)
        }),
        # ('Timestamps', { # If you want to show these explicitly
        #     'fields': ('created_at', 'updated_at'),
        #     'classes': ('collapse',) 
        # }),
    )
    
    # IMPORTANT: Logic to deduct stock on Sale completion is NOT YET IMPLEMENTED in the model.
    # Changing status to 'COMPLETED' here will not yet affect stock levels.

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('branch', 'processed_by') # Add 'customer' later

    # We can add custom actions here later, e.g., "Mark as Completed and Deduct Stock"

# SaleItem can also be registered separately if needed for direct access,
# but it's primarily managed via the Sale inline.
# @admin.register(SaleItem)
# class SaleItemAdmin(admin.ModelAdmin):
#     list_display = ('sale', 'product', 'quantity', 'unit_price_at_sale', 'total_price')
#     list_filter = ('sale__branch', 'product__category')
#     search_fields = ('sale__sale_number', 'product__name')
#     readonly_fields = ('total_price',)
#     autocomplete_fields = ['sale', 'product']
