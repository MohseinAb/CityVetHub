from django.db import models
from django.conf import settings
import uuid

# --- Community Forum Models ---
class CommunityPost(models.Model):
    CATEGORY_CHOICES = (
        ('GENERAL', 'General Discussion'),
        ('LOST_FOUND', 'Lost & Found Pets'),
        ('ADVICE', 'Pet Care & Health Advice'),
        ('RESCUE', 'Rescue Stories'),
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='community_posts')
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='GENERAL')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class PostComment(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


# --- Pet Adoption Models ---
class Pet(models.Model):
    STATUS_CHOICES = (
        ('AVAILABLE', 'Available for Adoption'),
        ('PENDING', 'Adoption Pending'),
        ('ADOPTED', 'Adopted'),
    )

    registered_pet = models.OneToOneField(
        'RegisteredPet',
        on_delete=models.CASCADE,
        related_name='adoption_listing'
    )
    adoption_reason = models.TextField(
        help_text="Why is this pet being put up for adoption (e.g. moving, rehoming rescue)?"
    )
    adoption_fee = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0.00,
        help_text="Enter 0.00 for free adoption"
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='AVAILABLE')
    listed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listed_pets')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.registered_pet.name} ({self.registered_pet.registration_number}) - {self.status}"


class AdoptionApplication(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved & Transferred'),
        ('REJECTED', 'Rejected'),
    )
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='adoption_applications')
    contact_number = models.CharField(max_length=20)
    address = models.CharField(max_length=255, help_text="Barangay, Iligan City")
    reason_for_adoption = models.TextField()
    has_other_pets = models.BooleanField(default=False, verbose_name="Do you currently have other pets?")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Application by {self.applicant.username} for {self.pet.registered_pet.name} ({self.status})"

class RegisteredPet(models.Model):
    SPECIES_CHOICES = (
        ('DOG', 'Dog'),
        ('CAT', 'Cat'),
        ('OTHER', 'Other'),
    )
    GENDER_CHOICES = (
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registered_pets')
    registration_number = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=10, choices=SPECIES_CHOICES, default='DOG')
    breed = models.CharField(max_length=100, default='Mixed / Aspin / Puspin')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    birth_date = models.DateField(null=True, blank=True, help_text="Approximate birth date if exact is unknown")
    color_markings = models.CharField(max_length=150, help_text="e.g., Brown with white chest")
    microchip_or_tag_id = models.CharField(max_length=100, blank=True, null=True, help_text="Optional Tag or Microchip Number")
    barangay = models.CharField(max_length=100, default="Tibanga", help_text="Residence barangay in Iligan City")
    photo = models.ImageField(upload_to='registered_pets/', blank=True, null=True)
    is_neutered = models.BooleanField(default=False, verbose_name="Spayed / Neutered")
    registered_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-generate a readable registry tag like ILG-PET-XXXX
        if not self.registration_number:
            self.registration_number = f"ILG-PET-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.name} ({self.registration_number}) - {self.owner.username}"


class VaccinationRecord(models.Model):
    VACCINE_TYPES = (
        ('RABIES', 'Anti-Rabies (Mandatory)'),
        ('5IN1', 'DHPP / 5-in-1 (Canine)'),
        ('6IN1', '6-in-1 / 8-in-1 (Canine)'),
        ('4IN1', 'FVRCP / 4-in-1 (Feline)'),
        ('DEWORM', 'Deworming'),
        ('OTHER', 'Other Vaccination'),
    )

    pet = models.ForeignKey(RegisteredPet, on_delete=models.CASCADE, related_name='vaccinations')
    vaccine_name = models.CharField(max_length=20, choices=VACCINE_TYPES, default='RABIES')
    administered_date = models.DateField()
    expiration_date = models.DateField(help_text="Next booster due date")
    administered_by = models.CharField(max_length=150, help_text="Veterinarian Name or Clinic / City Vet")
    batch_number = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(
        blank=True, 
        verbose_name="Clinical Notes / Description",
        help_text="Optional dosage details, pet weight, reactions, or next booster instructions."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-administered_date']

    def __str__(self):
        return f"{self.get_vaccine_name_display()} for {self.pet.name} on {self.administered_date}"

class PetAccessRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Access Granted'),
        ('REJECTED', 'Access Denied'),
    )

    pet = models.ForeignKey(RegisteredPet, on_delete=models.CASCADE, related_name='access_requests')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scan_requests')
    purpose = models.CharField(max_length=255, help_text="Reason for scanning (e.g., Found stray, Vet clinic verification)")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Scan Request by {self.requester.username} for {self.pet.name} ({self.status})"

class DiseaseAlert(models.Model):
    DISEASE_CHOICES = (
        ('RABIES', 'Rabies (Hydrophobia)'),
        ('PARVO', 'Canine Parvovirus (CPV)'),
        ('DISTEMPER', 'Canine Distemper Virus (CDV)'),
        ('PANLEUK', 'Feline Panleukopenia (FPV)'),
        ('LEPTO', 'Leptospirosis'),
        ('OTHER', 'Other Infectious Condition'),
    )

    SEVERITY_LEVELS = (
        ('LOW', 'Low - Watch / Isolated Case'),
        ('MODERATE', 'Moderate - Increasing Incidence'),
        ('HIGH', 'High - Active Cluster / Outbreak Warning'),
        ('CRITICAL', 'Critical - Quarantine / Immediate Action'),
    )

    STATUS_CHOICES = (
        ('UNVERIFIED', 'Pending City Vet Verification'),
        ('VERIFIED', 'Verified Outbreak Alert'),
        ('RESOLVED', 'Resolved / Contained'),
    )

    ILIGAN_BARANGAYS = [
        ('Abuno', 'Abuno'), ('Acmac', 'Acmac'), ('Bagong Silang', 'Bagong Silang'),
        ('Bonbonon', 'Bonbonon'), ('Buru-un', 'Buru-un'), ('Dalipuga', 'Dalipuga'),
        ('Del Carmen', 'Del Carmen'), ('Digkilaan', 'Digkilaan'), ('Ditucalan', 'Ditucalan'),
        ('Hinaplanon', 'Hinaplanon'), ('Kabacsanan', 'Kabacsanan'), ('Kiwalan', 'Kiwalan'),
        ('Lanipao', 'Lanipao'), ('Luinab', 'Luinab'), ('Mahayahay', 'Mahayahay'),
        ('Mainit', 'Mainit'), ('Mandulog', 'Mandulog'), ('Maria Cristina', 'Maria Cristina'),
        ('Pala-o', 'Pala-o'), ('Poblacion', 'Poblacion'), ('Puga-an', 'Puga-an'),
        ('San Miguel', 'San Miguel'), ('San Roque', 'San Roque'), ('Santa Elena', 'Santa Elena'),
        ('Santa Filomena', 'Santa Filomena'), ('Santiago', 'Santiago'), ('Sarigao', 'Sarigao'),
        ('Suarez', 'Suarez'), ('Tambacan', 'Tambacan'), ('Tibanga', 'Tibanga'),
        ('Tipanoy', 'Tipanoy'), ('Tomas Cabili', 'Tomas Cabili'), ('Tubod', 'Tubod'),
        ('Ubaldo Laya', 'Ubaldo Laya'), ('Upper Hinaplanon', 'Upper Hinaplanon'),
        ('Upper Tominobo', 'Upper Tominobo'), ('Villa Verde', 'Villa Verde'),('Saray', 'Saray'),
    ]

    title = models.CharField(max_length=200, help_text="e.g., Parvovirus Outbreak Cluster in Tibanga")
    disease = models.CharField(max_length=20, choices=DISEASE_CHOICES, default='PARVO')
    barangay = models.CharField(max_length=50, choices=ILIGAN_BARANGAYS, default='Tibanga')
    severity = models.CharField(max_length=15, choices=SEVERITY_LEVELS, default='MODERATE')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='UNVERIFIED')
    description = models.TextField(help_text="Symptoms observed, number of affected animals, and specific streets or puroks.")
    precautionary_measures = models.TextField(blank=True, help_text="Advisory notes for pet owners (e.g. avoid off-leash walks, get boosters).")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='disease_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title} ({self.barangay})"


class PetOwnershipHistory(models.Model):
    TRANSFER_TYPES = (
        ('ADOPTION', 'Official Platform Adoption'),
        ('MANUAL', 'Administrative / Manual Transfer'),
    )
    pet = models.ForeignKey('RegisteredPet', on_delete=models.CASCADE, related_name='ownership_history')
    previous_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='transferred_pets')
    new_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='acquired_pets')
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPES, default='ADOPTION')
    notes = models.TextField(blank=True, help_text="Reason or reference details for ownership transfer")
    transferred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transferred_at']

    def __str__(self):
        prev_name = self.previous_owner.username if self.previous_owner else "Unknown"
        new_name = self.new_owner.username if self.new_owner else "Unknown"
        return f"{self.pet.registration_number}: {prev_name} -> {new_name} ({self.transferred_at.strftime('%Y-%m-%d')})"

class Notification(models.Model):
    NOTIF_TYPES = (
        ('COMMENT', 'New Comment on Post'),
        ('MATCH', 'Pet Adoption Match'),
        ('ADOPTION', 'Adoption Update'),
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES)
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"To {self.recipient.username}: {self.message}"