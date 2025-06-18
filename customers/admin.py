from django.contrib import admin
from .models import Customer, CustomerLedgerEntry # Import CustomerLedgerEntry too for later

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_owner', 'email', 'phone_number', 'current_balance', 'can_purchase_on_credit')
    list_filter = ('company_owner', 'can_purchase_on_credit')
    search_fields = ('name', 'email', 'phone_number', 'company_owner__name') # CRITICAL for autocomplete
    list_editable = ('can_purchase_on_credit',) # Example
    # autocomplete_fields = ['company_owner'] # If you also want autocomplete for company_owner

    fieldsets = (
        (None, {'fields': ('company_owner', 'name', ('email', 'phone_number'), 'address')}),
        ('Credit Details', {'fields': ('can_purchase_on_credit', 'credit_limit', 'current_balance')}),
        ('Additional Info', {'fields': ('tax_id', 'notes')}),
    )
    readonly_fields = ('current_balance', 'created_at', 'updated_at') # current_balance is calculated

# We'll register CustomerLedgerEntry later when its logic is complete
# @admin.register(CustomerLedgerEntry)
# class CustomerLedgerEntryAdmin(admin.ModelAdmin):
#     list_display = ('entry_date', 'customer', 'entry_type', 'debit_amount', 'credit_amount', 'description')
#     list_filter = ('entry_type', 'customer__company_owner', 'customer')
#     search_fields = ('customer__name', 'description', 'sale__sale_number')
#     date_hierarchy = 'entry_date'
#     autocomplete_fields = ['customer', 'sale', 'created_by']
