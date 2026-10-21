from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from .forms import CustomUserCreationForm, UserProfileForm
from .models import VetVerificationRequest
from citizen.forms import VetVerificationForm

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
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Account profile updated successfully.")
                return redirect('accounts:profile')
        
        elif 'submit_vet' in request.POST:
            # Allow new submission or overwriting a rejected one
            vet_form = VetVerificationForm(request.POST, request.FILES, instance=vet_request)
            if vet_form.is_valid():
                vr = vet_form.save(commit=False)
                vr.user = user
                vr.status = 'PENDING'
                vr.save()
                messages.success(request, "Veterinary verification request submitted for CVO Admin approval.")
                return redirect('accounts:profile')
    else:
        profile_form = UserProfileForm(instance=user)
        vet_form = VetVerificationForm(instance=vet_request)

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'vet_form': vet_form,
        'vet_request': vet_request
    })