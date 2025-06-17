from django.db import models
from django.contrib.auth.models import User # Django's built-in User model
from organization.models import BusinessUnit # Your BusinessUnit model

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    # You can add specific permission flags here later if needed,
    # e.g., can_view_reports = models.BooleanField(default=False)
    # For now, the role name itself will imply permissions.

    def __str__(self):
        return self.name

class UserAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments')
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.CASCADE, related_name='user_assignments')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='user_assignments') # Protect roles from accidental deletion if assigned
    # on_delete=models.PROTECT for role means you can't delete a Role if users are assigned to it.

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'business_unit') # A user can only have one role per specific business unit.
                                                    # Adjust if a user can have multiple roles in the same unit.
        verbose_name = "User Assignment"
        verbose_name_plural = "User Assignments"

    def __str__(self):
        return f"{self.user.username} as {self.role.name} in {self.business_unit.name}"
