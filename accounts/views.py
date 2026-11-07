from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from .forms import CustomUserCreationForm
from .models import VetVerificationRequest
from .forms import UserProfileForm, PetPreferencesForm, VetVerificationForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash


# --- Registration View (Restored) ---
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful. Welcome to City Vet Hub!")
            return redirect('citizen:home')  # Adjust redirect destination if needed
    else:
        form = CustomUserCreationForm()
    
    # Ensure you have an 'accounts/register.html' or 'registration/register.html' template
    return render(request, 'accounts/register.html', {'form': form})


# --- Profile & Vet Verification View (New) ---
@login_required
def profile_view(request):
    user = request.user
    vet_request = VetVerificationRequest.objects.filter(user=user).first()

    profile_form = UserProfileForm(instance=user)
    pref_form = PetPreferencesForm(instance=user)
    password_form = PasswordChangeForm(user=user)
    vet_form = VetVerificationForm(instance=vet_request)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Personal information updated successfully.")
                return redirect('accounts:profile')

        elif 'update_preferences' in request.POST:
            pref_form = PetPreferencesForm(request.POST, instance=user)
            if pref_form.is_valid():
                pref_form.save()
                messages.success(request, "Adoption matching preferences saved! Check the Adoption Hub to see your matches.")
                return redirect('accounts:profile')

        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, "Your password has been changed successfully.")
                return redirect('accounts:profile')
            else:
                messages.error(request, "Please correct the password errors below.")

        elif 'submit_vet' in request.POST:
            vet_form = VetVerificationForm(request.POST, request.FILES, instance=vet_request)
            if vet_form.is_valid():
                vr = vet_form.save(commit=False)
                vr.user = user
                vr.status = 'PENDING'
                vr.save()
                messages.success(request, "Veterinary verification request submitted for CVO Admin approval.")
                return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'pref_form': pref_form,
        'password_form': password_form,
        'vet_form': vet_form,
        'vet_request': vet_request,
    })