from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('CITIZEN', 'Citizen / Pet Owner'),
        ('VET_CLINIC', 'Certified Private Vet'),
        ('VET_OFFICER', 'CVO Officer'),
        ('CVO_ADMIN', 'CVO System Admin'),
    )

    PREF_SPECIES_CHOICES = (
        ('ANY', 'Any Species'),
        ('DOG', 'Dog'),
        ('CAT', 'Cat'),
        ('OTHER', 'Other'),
    )
    PREF_GENDER_CHOICES = (
        ('ANY', 'Any Gender'),
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
    )
    pref_species = models.CharField(
        max_length=20, choices=PREF_SPECIES_CHOICES, default='ANY', verbose_name="Preferred Species"
    )
    pref_gender = models.CharField(
        max_length=15, choices=PREF_GENDER_CHOICES, default='ANY', verbose_name="Preferred Gender"
    )
    pref_breed = models.CharField(
        max_length=100, blank=True, help_text="Leave blank for any breed (e.g., Aspin, Puspin, Shih Tzu)", verbose_name="Preferred Breed Keyword"
    )
    pref_neutered_only = models.BooleanField(
        default=False, verbose_name="Prefer Neutered / Spayed Pets Only"
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