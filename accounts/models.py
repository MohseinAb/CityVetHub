from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('CITIZEN', 'Citizen / Pet Owner'),
        ('VET_CLINIC', 'Certified Private Vet'),
        ('VET_OFFICER', 'CVO Officer'),
        ('CVO_ADMIN', 'CVO System Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CITIZEN')

    def __str__(self):
        return self.username


class VetVerificationRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='vet_verification')
    clinic_name = models.CharField(max_length=255, help_text="Name of the veterinary clinic")
    prc_license_number = models.CharField(max_length=50, unique=True, help_text="PRC License Number")
    proof_document = models.ImageField(upload_to='vet_proofs/', help_text="Upload PRC ID or Business Permit")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Vet Request: {self.user.username} - {self.status}"