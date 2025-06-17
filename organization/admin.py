from django.contrib import admin
from .models import BusinessUnit # Import your BusinessUnit model

@admin.register(BusinessUnit) # This is the modern way to register
class BusinessUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit_type', 'parent', 'email', 'phone_number', 'created_at')
    list_filter = ('unit_type', 'parent') # Add filters to the sidebar
    search_fields = ('name', 'email', 'phone_number') # Add a search box
    list_editable = ('unit_type', 'parent') # Allows direct editing in the list view (use with caution)

    # Optional: For better display of the parent field, especially with many units
    # autocomplete_fields = ['parent'] # Requires some setup in the parent model's admin if you have many

    # Optional: Customize the form layout
    # fields = (('name', 'unit_type'), 'parent', ('address', 'phone_number', 'email'), 'timezone')

    # Optional: To make the hierarchy more visible, you might consider using django-mptt or similar
    # for a tree-like display in the admin, but for now, this is a good start.

# Alternative, older way to register (either way works):
# admin.site.register(BusinessUnit, BusinessUnitAdmin)
