from django.db import models

class BusinessUnit(models.Model):
    class UnitType(models.TextChoices):
        GROUP = 'GROUP', 'Group'
        COMPANY = 'COMPANY', 'Company'
        BRANCH = 'BRANCH', 'Branch'

    name = models.CharField(max_length=255)
    unit_type = models.CharField(
        max_length=10,
        choices=UnitType.choices,
        default=UnitType.BRANCH,
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE, # If a parent is deleted, delete its children
        null=True,                # Top-level units have no parent
        blank=True,               # Parent is optional in forms
        related_name='children'   # How to get children from a parent instance
    )
    address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    timezone = models.CharField(max_length=50, default='UTC', blank=True, null=True) # Or a more specific default
    # Add other common fields like tax_id, registration_number, etc. if needed

    # FBR integration related fields (can be added later, but good to think about)
    # fbr_api_key = models.CharField(max_length=255, blank=True, null=True)
    # fbr_pos_id = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Business Unit"
        verbose_name_plural = "Business Units"
        ordering = ['name'] # Default ordering when querying

    def __str__(self):
        return f"{self.name} ({self.get_unit_type_display()})"

    # Optional: Add a property to easily get the full path (e.g., "Big Food / Cheesy Pizza / Branch A")
    # This can be useful for display purposes.
    # def get_full_path(self):
    #     path = [self.name]
    #     current = self.parent
    #     while current:
    #         path.insert(0, current.name)
    #         current = current.parent
    #     return " / ".join(path)from django.db import models
