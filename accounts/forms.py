from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, VetVerificationRequest

# --- Registration Form (Restored) ---
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email')

# --- Profile Update Form (New) ---
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class PetPreferencesForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['pref_species', 'pref_gender', 'pref_breed', 'pref_neutered_only']
        widgets = {
            'pref_species': forms.Select(attrs={'class': 'form-select'}),
            'pref_gender': forms.Select(attrs={'class': 'form-select'}),
            'pref_breed': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Aspin, Puspin, Golden Retriever (Optional)'}),
            'pref_neutered_only': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class VetVerificationForm(forms.ModelForm):
    class Meta:
        model = VetVerificationRequest
        fields = ['clinic_name', 'prc_license_number', 'proof_document']
        widgets = {
            'clinic_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Iligan Animal Care Clinic'}),
            'prc_license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 0123456'}),
            'proof_document': forms.FileInput(attrs={'class': 'form-control'}),
        }