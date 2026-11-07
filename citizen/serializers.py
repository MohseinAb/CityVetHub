from rest_framework import serializers

from officer.views import ILIGAN_BARANGAY_COORDS
from .models import (
    RegisteredPet, VaccinationRecord, CommunityPost, 
    PostComment, Pet, AdoptionApplication, DiseaseAlert, 
    Notification, PetAccessRequest
)
from django.contrib.auth import get_user_model

User = get_user_model()

class VaccinationRecordSerializer(serializers.ModelSerializer):
    vaccine_display = serializers.CharField(source='get_vaccine_name_display', read_only=True)

    class Meta:
        model = VaccinationRecord
        fields = ['id', 'vaccine_name', 'vaccine_display', 'administered_date', 'expiration_date', 'administered_by', 'batch_number', 'notes']

class RegisteredPetSerializer(serializers.ModelSerializer):
    owner_username = serializers.ReadOnlyField(source='owner.username')
    vaccinations = VaccinationRecordSerializer(many=True, read_only=True)
    species_display = serializers.CharField(source='get_species_display', read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)

    class Meta:
        model = RegisteredPet
        fields = [
            'id', 'registration_number', 'name', 'species', 'species_display', 
            'breed', 'gender', 'gender_display', 'birth_date', 'color_markings', 
            'microchip_or_tag_id', 'barangay', 'photo', 'is_neutered', 
            'owner_username', 'vaccinations', 'registered_at'
        ]

class PostCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = PostComment
        fields = ['id', 'author_username', 'content', 'created_at']

class CommunityPostSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    comments = PostCommentSerializer(many=True, read_only=True)

    class Meta:
        model = CommunityPost
        fields = ['id', 'author_username', 'title', 'category', 'category_display', 'content', 'comments', 'created_at']

class PetAdoptionSerializer(serializers.ModelSerializer):
    registered_pet_details = RegisteredPetSerializer(source='registered_pet', read_only=True)
    listed_by_username = serializers.ReadOnlyField(source='listed_by.username')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_match = serializers.SerializerMethodField()

    class Meta:
        model = Pet
        fields = [
            'id', 'registered_pet', 'registered_pet_details', 
            'adoption_reason', 'adoption_fee', 'status', 
            'status_display', 'listed_by_username', 'is_match', 'created_at'
        ]

    def get_is_match(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        user = request.user
        pet = obj.registered_pet

        # Checks preferences directly on User or a related UserPreference model
        prefs = getattr(user, 'preferences', user)
        
        pref_species = getattr(prefs, 'preferred_species', None)
        pref_gender = getattr(prefs, 'preferred_gender', None)
        pref_barangay = getattr(prefs, 'preferred_barangay', None) or getattr(user, 'barangay', None)

        # Match if the pet aligns with the user's saved species/gender/barangay preferences
        if pref_species and pref_species != 'ANY' and pet.species != pref_species:
            return False
        if pref_gender and pref_gender != 'ANY' and pet.gender != pref_gender:
            return False
        if pref_barangay and pref_barangay != 'ANY' and pet.barangay != pref_barangay:
            return False

        # Return True if the user actually set at least one preference and it matched
        return any([pref_species, pref_gender, pref_barangay])

class DiseaseAlertSerializer(serializers.ModelSerializer):
    disease_display = serializers.CharField(source='get_disease_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reporter_username = serializers.ReadOnlyField(source='reporter.username')
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = DiseaseAlert
        fields = [
            'id', 'title', 'disease', 'disease_display', 'barangay', 
            'severity', 'severity_display', 'status', 'status_display', 
            'description', 'precautionary_measures', 'reporter_username', 
            'latitude', 'longitude', 'created_at'
        ]

    def get_latitude(self, obj):
        coords = ILIGAN_BARANGAY_COORDS.get(obj.barangay)
        return coords[0] if coords else None

    def get_longitude(self, obj):
        coords = ILIGAN_BARANGAY_COORDS.get(obj.barangay)
        return coords[1] if coords else None

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notif_type', 'message', 'link', 'is_read', 'created_at']

class AdoptionApplicationSerializer(serializers.ModelSerializer):
    applicant_username = serializers.ReadOnlyField(source='applicant.username')

    class Meta:
        model = AdoptionApplication
        fields = [
            'id', 'pet', 'applicant_username', 'contact_number', 
            'address', 'reason_for_adoption', 'has_other_pets', 
            'status', 'applied_at'
        ]
        read_only_fields = ['status', 'applied_at']

class PetAccessRequestSerializer(serializers.ModelSerializer):
    requester_username = serializers.ReadOnlyField(source='requester.username')

    class Meta:
        model = PetAccessRequest
        fields = ['id', 'pet', 'requester_username', 'purpose', 'status', 'requested_at']
        read_only_fields = ['status', 'requested_at']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        # If your CustomUser in accounts/models.py has extra fields like 'role' or 'phone_number', add them to this list!
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class UserProfileAndPreferenceSerializer(serializers.ModelSerializer):
    """Handles viewing & editing profile info AND adoption preferences."""
    class Meta:
        model = User
        # Dynamic: grabs standard fields + any custom profile/preference fields on your User model
        fields = [
            f.name for f in User._meta.fields 
            if f.name not in ('password', 'is_superuser', 'is_staff', 'is_active', 'last_login')
        ]
        read_only_fields = ['id', 'username', 'date_joined', 'role']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=6)