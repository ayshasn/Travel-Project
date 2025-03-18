from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """ Model to extend Django's User model for Managers and Employees """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    
    ROLE_CHOICES = (
        ("manager", "Manager"),
        ("employee", "Employee"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Admin(models.Model):
    """ Model to extend Django's User model for Admins """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)  # Ensure this stores hashed passwords
    email_id = models.EmailField(max_length=100, unique=True)

    def __str__(self):
        return self.username

class Manager(models.Model):
    """ Model to extend Django's User model for Managers """
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="manager_profile")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, default="Not Specified")  
    email = models.EmailField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=UserProfile.STATUS_CHOICES, default="active")
    designation = models.CharField(max_length=20, default="HR")

    def __str__(self):
        return f"Manager: {self.first_name} {self.last_name}"


class Employee(models.Model):
    """ Model to extend Django's User model for Employees """
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="employee_profile")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, default="Not Specified")  
    email = models.EmailField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=UserProfile.STATUS_CHOICES, default="active")
    designation = models.CharField(max_length=20, default="HR")
    manager = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Employee: {self.first_name} {self.last_name}"


class TravelRequest(models.Model):
    """ Model to store travel requests from Employees """
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    manager = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True, blank=True)
    from_location = models.CharField(max_length=50)
    to_location = models.CharField(max_length=50)
    
    TRAVEL_MODE_CHOICES = (
        ("Air", "Air"),
        ("Ship", "Ship"),
        ("Train", "Train"),
        ("Bus", "Bus"),
        ("Car", "Car"),
    )
    travel_mode = models.CharField(max_length=20, choices=TRAVEL_MODE_CHOICES)

    additional_notes = models.CharField(max_length=100, blank=True, null=True)
    manager_notes = models.CharField(max_length=100, blank=True, null=True)
    admin_notes = models.CharField(max_length=100, blank=True, null=True)

    STATUS_CHOICES = (
        ("approved", "Approved"),
        ("pending", "Pending"),
        ("rejected", "Rejected"),
        ("closed", "Closed"),
        ("update", "Update"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    date_submitted = models.DateField(auto_now_add=True)
    update_submitted_date = models.DateField(null=True, blank=True)  # Handled via logic

    start_date = models.DateField()
    end_date = models.DateField()
    hotel_preference = models.CharField(max_length=100, blank=True, null=True)
    lodging_required = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    is_resubmitted = models.BooleanField(default=False)
    resubmitted_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Travel Request from {self.from_location} to {self.to_location} ({self.status})"
