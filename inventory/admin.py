from django.contrib import admin
from .models import InventoryStock, GoodsReceiveNote, GRNItem

@admin.register(InventoryStock)
class InventoryStockAdmin(admin.ModelAdmin):
    list_display = ('product', 'branch', 'quantity', 'last_updated')
    list_filter = ('branch', 'product__category', 'product__company_owner')
    search_fields = ('product__name', 'product__sku', 'branch__name')
    readonly_fields = ('last_updated',) # Quantity should ideally be updated via GRNs and Sales, not direct edit
    list_per_page = 25

    # To make this truly useful, direct editing of quantity should be restricted.
    # It's better to manage stock through GRNs and Sales transactions.
    # You might even make 'quantity' readonly or remove 'InventoryStock' from direct admin editing
    # for most users once transactional logic is in place.
    # For now, it's useful for initial setup or corrections by an admin.

    def get_queryset(self, request):
        # Optimize query by prefetching related objects
        return super().get_queryset(request).select_related('product', 'branch', 'product__company_owner')


class GRNItemInline(admin.TabularInline): # Or StackedInline
    model = GRNItem
    extra = 1 # Number of empty forms to display for new GRNs
    autocomplete_fields = ['product']
    # Add readonly_fields for completed GRNs later
    
    # Consider adding a check to only allow products that belong to the GRN's branch's company owner


@admin.register(GoodsReceiveNote)
class GoodsReceiveNoteAdmin(admin.ModelAdmin):
    list_display = ('grn_number', 'branch', 'supplier', 'received_date', 'status', 'received_by', 'updated_at')
    list_filter = ('branch', 'supplier', 'status', 'received_date', 'received_by')
    search_fields = ('grn_number', 'supplier_invoice_number', 'branch__name', 'supplier__name')
    readonly_fields = ('created_at', 'updated_at') # Standard audit fields
    autocomplete_fields = ['branch', 'supplier', 'received_by']
    date_hierarchy = 'received_date'
    inlines = [GRNItemInline] # Allows adding GRNItems directly when creating/editing a GRN
    list_per_page = 20

    fieldsets = (
        (None, {
            'fields': ('grn_number', ('branch', 'supplier'), ('received_date', 'status'))
        }),
        ('Details', {
            'fields': ('supplier_invoice_number', 'notes', 'received_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',) # Collapsible section
        }),
    )

    # IMPORTANT: Logic to update stock on GRN completion is NOT YET IMPLEMENTED.
    # This will be added to the model's save() method or via signals.
    # For now, changing status to 'COMPLETED' in admin does not update stock.

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('branch', 'supplier', 'received_by')

    # We can add custom actions here later, e.g., "Mark as Completed and Update Stock"


# GRNItem can also be registered separately if needed for direct access,
# but it's primarily managed via the GRN inline.
# @admin.register(GRNItem)
# class GRNItemAdmin(admin.ModelAdmin):
#     list_display = ('grn', 'product', 'quantity_received', 'cost_price_per_unit')
#     list_filter = ('grn__branch', 'product__category')
#     search_fields = ('grn__grn_number', 'product__name')
#     autocomplete_fields = ['grn', 'product']
