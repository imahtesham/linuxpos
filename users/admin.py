from django.contrib import admin
from .models import Role, UserAssignment

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(UserAssignment)
class UserAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'business_unit', 'role', 'created_at')
    list_filter = ('role', 'business_unit__unit_type', 'business_unit') # Filter by role, unit type, or specific unit
    search_fields = ('user__username', 'user__email', 'business_unit__name', 'role__name')
    autocomplete_fields = ['user', 'business_unit', 'role'] # Makes selecting easier

    # To improve the display of business_unit in filters/dropdowns if you have many
    # You might need to ensure the __str__ method of BusinessUnit is clear
    # Or customize the formfield_for_foreignkey method if needed for complex filtering
