from django.contrib import admin
from .models import Customer, CustomerLedgerEntry

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_owner', 'email', 'phone_number', 'current_balance', 'can_purchase_on_credit', 'updated_at')
    list_filter = ('company_owner', 'can_purchase_on_credit')
    search_fields = ('name', 'email', 'phone_number', 'company_owner__name')
    list_editable = ('can_purchase_on_credit',)
    autocomplete_fields = ['company_owner'] # If you want autocomplete for company_owner

    fieldsets = (
        (None, {'fields': ('company_owner', 'name', ('email', 'phone_number'), 'address')}),
        ('Credit Details', {'fields': ('can_purchase_on_credit', 'credit_limit', 'current_balance')}),
        ('Additional Info', {'fields': ('tax_id', 'notes')}),
        ('Audit', {'fields': (('created_at', 'updated_at'),), 'classes': ('collapse',)}),
    )
    readonly_fields = ('current_balance', 'created_at', 'updated_at')

@admin.register(CustomerLedgerEntry) # <<< UNCOMMENTED AND DEFINED
class CustomerLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'customer', 'entry_type', 'debit_amount', 'credit_amount', 'description', 'sale_link')
    list_filter = ('entry_type', 'customer__company_owner', 'customer', 'entry_date')
    search_fields = ('customer__name', 'description', 'sale__sale_number')
    date_hierarchy = 'entry_date' # Allows drilling down by date
    autocomplete_fields = ['customer', 'sale', 'created_by']
    list_select_related = ('customer', 'sale', 'created_by') # For performance
    list_per_page = 25
    readonly_fields = ('entry_date',) # entry_date is auto_now_add

    fieldsets = (
        (None, {'fields': ('customer', 'entry_type', 'entry_date')}),
        ('Amounts', {'fields': (('debit_amount', 'credit_amount'),)}),
        ('Details', {'fields': ('description', 'sale', 'created_by')}),
    )

    def get_queryset(self, request):
        # Optimize query
        return super().get_queryset(request).select_related('customer', 'sale', 'created_by', 'customer__company_owner')

    def sale_link(self, obj):
        # Creates a clickable link to the related sale in the admin
        from django.urls import reverse
        from django.utils.html import format_html
        if obj.sale:
            link = reverse("admin:sales_sale_change", args=[obj.sale.pk])
            return format_html('<a href="{}">{}</a>', link, obj.sale)
        return "-"
    sale_link.short_description = 'Related Sale'
    sale_link.admin_order_field = 'sale' # Allows sorting by sale (though might be slow without good indexing)
