from django import forms
from .models import (
    CommunityPost,
    PostComment,
    Pet,
    AdoptionApplication,
    RegisteredPet,
    VaccinationRecord,
    DiseaseAlert,
)
from accounts.models import VetVerificationRequest


class CommunityPostForm(forms.ModelForm):
    class Meta:
        model = CommunityPost
        fields = ('title', 'category', 'content')
        widgets = {
            'content': forms.Textarea(
                attrs={
                    'rows': 5,
                    'placeholder': 'Share details, asks, or stories...',
                }
            ),
        }


class PostCommentForm(forms.ModelForm):
    class Meta:
        model = PostComment
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Write a reply...'}
            ),
        }
        labels = {'content': ''}


class PetAdoptionListingForm(forms.ModelForm):
    registered_pet = forms.ModelChoiceField(
        queryset=RegisteredPet.objects.none(),
        label="Select Registered Pet",
        help_text="Choose one of your registered pets to put up for adoption.",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Pet
        fields = ('registered_pet', 'adoption_fee', 'adoption_reason')
        widgets = {
            'adoption_reason': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Explain pet personality, reason for rehoming, and any specific adopter requirements...'
            }),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only display pets owned by the active user that are NOT already listed
        self.fields['registered_pet'].queryset = RegisteredPet.objects.filter(
            owner=user,
            adoption_listing__isnull=True
        )


class PetAdoptionUpdateForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ('adoption_fee', 'adoption_reason', 'status')
        widgets = {
            'adoption_reason': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'adoption_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class AdoptionApplicationForm(forms.ModelForm):
    class Meta:
        model = AdoptionApplication
        fields = (
            'contact_number',
            'address',
            'has_other_pets',
            'reason_for_adoption',
        )
        widgets = {
            'reason_for_adoption': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': 'Tell us why you would be a great parent for this pet...',
                }
            ),
        }


class RegisteredPetForm(forms.ModelForm):
    class Meta:
        model = RegisteredPet
        fields = (
            'name',
            'species',
            'breed',
            'gender',
            'birth_date',
            'color_markings',
            'microchip_or_tag_id',
            'barangay',
            'photo',
            'is_neutered',
        )
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }


class VaccinationRecordForm(forms.ModelForm):
    class Meta:
        model = VaccinationRecord
        fields = (
            'vaccine_name',
            'administered_date',
            'expiration_date',
            'administered_by',
            'batch_number',
        )
        widgets = {
            'administered_date': forms.DateInput(attrs={'type': 'date'}),
            'expiration_date': forms.DateInput(attrs={'type': 'date'}),
        }


class DiseaseReportForm(forms.ModelForm):
    class Meta:
        model = DiseaseAlert
        fields = ('title', 'disease', 'barangay', 'severity', 'description', 'precautionary_measures')
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Specify purok/street, pet symptoms, and approximate count of symptomatic animals...'
            }),
            'precautionary_measures': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Recommended actions for nearby pet owners...'
            }),
        }


class VaccinationRecordForm(forms.ModelForm):
    class Meta:
        model = VaccinationRecord
        fields = (
            'vaccine_name',
            'administered_date',
            'expiration_date',
            'administered_by',
            'batch_number',
            'notes',
        )
        widgets = {
            'administered_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expiration_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'Add clinical notes, dosage, weight at time of shot, or follow-up remarks...'
            }),
        }