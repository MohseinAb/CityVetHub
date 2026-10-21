from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import (
    PetOwnershipHistory,
)
from .forms import (
    CommunityPostForm,
    PostCommentForm,
    PetAdoptionListingForm,
    AdoptionApplicationForm,
    RegisteredPetForm,
    VaccinationRecordForm,
    PetAdoptionUpdateForm,
)
import qrcode
import io
import base64
from django.utils import timezone
from .models import (
    CommunityPost, Pet, AdoptionApplication,
    RegisteredPet, VaccinationRecord, PetAccessRequest
)
from .models import DiseaseAlert
from .forms import DiseaseReportForm
from django.db import transaction


# --- 1. Citizen Home & Forum Views ---
def is_officer_or_admin(user):
    return user.is_authenticated and (
        getattr(user, 'role', '') in ['VET_OFFICER', 'CVO_ADMIN'] or user.is_superuser
    )

def citizen_home(request):
    """Portal homepage: no outbreak alerts passed to non-officers."""
    recent_posts = CommunityPost.objects.select_related('author').order_by('-created_at')[:3]
    available_pets = Pet.objects.filter(status='AVAILABLE').select_related('registered_pet')[:4]
    
    return render(request, 'citizen/home.html', {
        'recent_posts': recent_posts,
        'available_pets': available_pets,
    })


def community_feed(request):
    """Reddit-like forum feed with category filtering."""
    category = request.GET.get('category')
    if category:
        posts = CommunityPost.objects.filter(category=category)
    else:
        posts = CommunityPost.objects.all()
    return render(request, 'citizen/community_feed.html', {
        'posts': posts,
        'selected_category': category
    })


@login_required
def create_post(request):
    """Create a new discussion thread."""
    if request.method == 'POST':
        form = CommunityPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('citizen:post_detail', pk=post.pk)
    else:
        form = CommunityPostForm()
    return render(request, 'citizen/create_post.html', {'form': form})


def post_detail(request, pk):
    """Read thread details and submit replies."""
    post = get_object_or_404(CommunityPost, pk=pk)
    comments = post.comments.all()
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')
        comment_form = PostCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect('citizen:post_detail', pk=post.pk)
    else:
        comment_form = PostCommentForm()

    return render(request, 'citizen/post_detail.html', {
        'post': post,
        'comments': comments,
        'comment_form': comment_form
    })


# --- 2. Pet Adoption Views ---
def pet_list(request):
    pets = Pet.objects.filter(status='AVAILABLE').select_related('registered_pet', 'listed_by')
    
    incoming_applications = []
    my_applications = []
    
    if request.user.is_authenticated:
        # 1. Requests sent TO the current user's listed pets
        incoming_applications = AdoptionApplication.objects.filter(
            pet__listed_by=request.user
        ).select_related('pet__registered_pet', 'applicant').order_by('-applied_at')
        
        # 2. Requests sent BY the current user to adopt other pets
        my_applications = AdoptionApplication.objects.filter(
            applicant=request.user
        ).select_related('pet__registered_pet', 'pet__listed_by').order_by('-applied_at')

    return render(request, 'citizen/pet_list.html', {
        'pets': pets,
        'incoming_applications': incoming_applications,
        'my_applications': my_applications,
    })

def pet_detail(request, pk):
    """Detailed view showing registry details, vaccine count, and adoption application."""
    pet = get_object_or_404(Pet.objects.select_related('registered_pet', 'listed_by'), pk=pk)
    vaccinations = pet.registered_pet.vaccinations.all()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')
        form = AdoptionApplicationForm(request.POST)
        if form.is_valid():
            app = form.save(commit=False)
            app.pet = pet
            app.applicant = request.user
            app.save()
            messages.success(request, f"Adoption inquiry sent for {pet.registered_pet.name}!")
            return redirect('citizen:pet_detail', pk=pet.pk)
    else:
        form = AdoptionApplicationForm()

    return render(request, 'citizen/pet_detail.html', {
        'pet': pet,
        'vaccinations': vaccinations,
        'form': form
    })


@login_required
def list_pet_for_adoption(request):
    """Pet selector form for citizen owners."""
    # Check if the user has any pets eligible to list
    unlisted_pets_count = RegisteredPet.objects.filter(owner=request.user, adoption_listing__isnull=True).count()

    if request.method == 'POST':
        form = PetAdoptionListingForm(request.user, request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.listed_by = request.user
            listing.save()
            messages.success(request, f"{listing.registered_pet.name} has been listed for adoption!")
            return redirect('citizen:pet_detail', pk=listing.pk)
    else:
        form = PetAdoptionListingForm(request.user)

    return render(request, 'citizen/list_pet.html', {
        'form': form,
        'unlisted_pets_count': unlisted_pets_count
    })


# --- 3. Pet Registry Views ---
@login_required
def my_pets_list(request):
    """List of pets registered by the currently logged-in citizen."""
    pets = RegisteredPet.objects.filter(owner=request.user)
    return render(request, 'citizen/my_pets_list.html', {'pets': pets})


@login_required
def register_pet(request):
    """Form to register a new pet into the municipal database."""
    if request.method == 'POST':
        form = RegisteredPetForm(request.POST, request.FILES)
        if form.is_valid():
            pet = form.save(commit=False)
            pet.owner = request.user
            pet.save()
            messages.success(request, f"{pet.name} has been registered with ID: {pet.registration_number}")
            return redirect('citizen:pet_passport', pk=pet.pk)
    else:
        form = RegisteredPetForm()

    return render(request, 'citizen/register_pet.html', {'form': form})


@login_required
def pet_passport(request, pk):
    """Owner's view: Generates dynamic QR Code and manages pending access requests."""
    pet = get_object_or_404(RegisteredPet, pk=pk, owner=request.user)
    vaccinations = pet.vaccinations.all()
    access_requests = pet.access_requests.filter(status='PENDING')

    if request.method == 'POST':
        vax_form = VaccinationRecordForm(request.POST)
        if vax_form.is_valid():
            vax = vax_form.save(commit=False)
            vax.pet = pet
            vax.save()
            messages.success(request, f"Added {vax.get_vaccine_name_display()} record!")
            return redirect('citizen:pet_passport', pk=pet.pk)
    else:
        vax_form = VaccinationRecordForm()

    # Generate QR Code pointing to the scan resolution endpoint
    scan_url = request.build_absolute_uri(f"/citizen/pets/scan/{pet.registration_number}/")
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(scan_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#198754", back_color="white") # Bootstrap green

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'citizen/pet_passport.html', {
        'pet': pet,
        'vaccinations': vaccinations,
        'vax_form': vax_form,
        'qr_base64': qr_base64,
        'access_requests': access_requests,
        'scan_url': scan_url,
    })

@login_required
def scan_pet_qr(request, reg_num):
    """Destination when QR code is scanned by any user or mobile app."""
    pet = get_object_or_404(RegisteredPet, registration_number=reg_num)

    # 1. If owner scans their own pet, redirect straight to the full passport
    if pet.owner == request.user:
        return redirect('citizen:pet_passport', pk=pet.pk)

    # 2. Check if this scanner already has an approved request
    existing_approved = PetAccessRequest.objects.filter(
        pet=pet, requester=request.user, status='APPROVED'
    ).first()

    if existing_approved:
        # Scanner is authorized -> show details
        vaccinations = pet.vaccinations.all()
        return render(request, 'citizen/scanner_pet_detail.html', {
            'pet': pet,
            'vaccinations': vaccinations,
        })

    # 3. Check if there is already a pending request
    pending_request = PetAccessRequest.objects.filter(  
        pet=pet, requester=request.user, status='PENDING'
    ).first()

    if request.method == 'POST' and not pending_request:
        purpose = request.POST.get('purpose', 'Identification verification')
        PetAccessRequest.objects.create(
            pet=pet,
            requester=request.user,
            purpose=purpose
        )
        messages.success(request, f"Access request sent to {pet.owner.username}. Please wait for them to approve.")
        return redirect('citizen:scan_pet_qr', reg_num=reg_num)

    return render(request, 'citizen/request_access.html', {
        'pet': pet,
        'pending_request': pending_request,
    })


@login_required
def manage_access_request(request, request_id, action):
    """Owner endpoint to approve or reject a scan request."""
    access_request = get_object_or_404(
        PetAccessRequest, id=request_id, pet__owner=request.user
    )

    if action == 'approve':
        access_request.status = 'APPROVED'
        access_request.reviewed_at = timezone.now()
        access_request.save()
        messages.success(request, f"Granted {access_request.requester.username} access to view {access_request.pet.name}'s info.")
    elif action == 'reject':
        access_request.status = 'REJECTED'
        access_request.reviewed_at = timezone.now()
        access_request.save()
        messages.warning(request, f"Denied access to {access_request.requester.username}.")

    return redirect('citizen:pet_passport', pk=access_request.pet.pk)

@login_required
def disease_alerts(request):
    if not is_officer_or_admin(request.user):
        messages.error(request, "Access restricted.")
        return redirect('citizen:home')

    alerts = DiseaseAlert.objects.all().order_by('-created_at') # <-- ERROR HERE
    return render(request, 'citizen/disease_alerts.html', {'alerts': alerts})

def disease_alerts_list(request):
    """Public advisory bulletin of active disease outbreaks across Iligan City."""
    selected_barangay = request.GET.get('barangay')
    selected_disease = request.GET.get('disease')

    alerts = DiseaseAlert.objects.all()

    if selected_barangay:
        alerts = alerts.filter(barangay=selected_barangay)
    if selected_disease:
        alerts = alerts.filter(disease=selected_disease)

    # High priority alerts count
    active_critical_count = DiseaseAlert.objects.filter(severity__in=['HIGH', 'CRITICAL'], status='VERIFIED').count()

    return render(request, 'citizen/disease_alerts.html', {
        'alerts': alerts,
        'barangays': DiseaseAlert.ILIGAN_BARANGAYS,
        'diseases': DiseaseAlert.DISEASE_CHOICES,
        'selected_barangay': selected_barangay,
        'selected_disease': selected_disease,
        'active_critical_count': active_critical_count,
    })


def disease_alert_detail(request, pk):
    """Detailed view for a specific disease outbreak advisory."""
    alert = get_object_or_404(DiseaseAlert, pk=pk)
    return render(request, 'citizen/disease_alert_detail.html', {'alert': alert})

@login_required
def report_disease(request):
    """Dedicated form for citizens to privately submit a disease/symptom report to CVO."""
    if request.method == 'POST':
        form = DiseaseReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            # Keep unverified/private until an officer reviews it
            if hasattr(report, 'is_verified'):
                report.is_verified = False
            report.save()
            messages.success(
                request, 
                "Your animal health report has been securely transmitted to the Iligan City Veterinary Office for investigation."
            )
            return redirect('citizen:home')
    else:
        form = DiseaseReportForm()

    return render(request, 'citizen/report_disease.html', {'form': form})

@login_required
def report_disease_incident(request):
    """Submit a disease outbreak flag or suspicious cluster."""
    if request.method == 'POST':
        form = DiseaseReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            # If user is a designated officer, auto-verify; otherwise unverified pending review
            if getattr(request.user, 'role', '') == 'VET_OFFICER':
                report.status = 'VERIFIED'
            else:
                report.status = 'UNVERIFIED'
            report.save()
            messages.success(request, "Incident report submitted. City Veterinary health units have been notified.")
            return redirect('citizen:disease_alerts')
    else:
        form = DiseaseReportForm()

    return render(request, 'citizen/report_disease.html', {'form': form})

# --- 1. OP Community Post Edit & Delete ---
@login_required
def edit_community_post(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    if post.author != request.user and not (getattr(request.user, 'role', '') == 'CVO_ADMIN' or request.user.is_superuser):
        messages.error(request, "You do not have permission to edit this post.")
        return redirect('citizen:community_feed')

    if request.method == 'POST':
        form = CommunityPostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated successfully.")
            return redirect('citizen:community_feed')
    else:
        form = CommunityPostForm(instance=post)

    return render(request, 'citizen/post_form.html', {'form': form, 'edit_mode': True, 'post': post})

@login_required
def delete_community_post(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    if post.author != request.user and not (getattr(request.user, 'role', '') == 'CVO_ADMIN' or request.user.is_superuser):
        messages.error(request, "You do not have permission to delete this post.")
        return redirect('citizen:community_feed')

    if request.method == 'POST':
        post.delete()
        messages.success(request, "Your post has been removed.")
    return redirect('citizen:community_feed')

# --- 2. OP Adoption Listing Edit & Delete ---
@login_required
def edit_adoption_listing(request, pet_id):
    listing = get_object_or_404(Pet, id=pet_id)
    if listing.listed_by != request.user and not (getattr(request.user, 'role', '') == 'CVO_ADMIN' or request.user.is_superuser):
        messages.error(request, "You can only edit your own adoption listings.")
        return redirect('citizen:pet_list')

    if request.method == 'POST':
        form = PetAdoptionUpdateForm(request.POST, instance=listing)
        if form.is_valid():
            form.save()
            messages.success(request, f"Adoption listing for {listing.registered_pet.name} updated.")
            return redirect('citizen:pet_detail', pk=listing.id) # Adjust if your detail URL name differs
    else:
        form = PetAdoptionUpdateForm(instance=listing)

    return render(request, 'citizen/adoption_edit_form.html', {'form': form, 'listing': listing})

@login_required
def delete_adoption_listing(request, pet_id):
    listing = get_object_or_404(Pet, id=pet_id)
    if listing.listed_by != request.user and not (getattr(request.user, 'role', '') == 'CVO_ADMIN' or request.user.is_superuser):
        messages.error(request, "You can only remove your own adoption listings.")
        return redirect('citizen:pet_list')

    if request.method == 'POST':
        pet_name = listing.registered_pet.name
        listing.delete()
        messages.success(request, f"Adoption listing for {pet_name} has been removed. The pet remains in your registry.")
    return redirect('citizen:pet_list')

# --- 3. Finalize Adoption & Ownership Transfer ---
@login_required
@transaction.atomic
def finalize_adoption(request, app_id, action):
    application = get_object_or_404(AdoptionApplication, id=app_id)
    listing = application.pet
    reg_pet = listing.registered_pet

    # Only the current pet owner / lister can approve or reject applications
    if listing.listed_by != request.user and reg_pet.owner != request.user:
        messages.error(request, "Unauthorized action.")
        return redirect('citizen:pet_list')

    if action == 'approve':
        old_owner = reg_pet.owner
        new_owner = application.applicant

        # 1. Log permanent Ownership History on the pet's record
        PetOwnershipHistory.objects.create(
            pet=reg_pet,
            previous_owner=old_owner,
            new_owner=new_owner,
            transfer_type='ADOPTION',
            notes=f"Official adoption transfer from {old_owner.username} to {new_owner.username}. Adopter address: {application.address}."
        )

        # 2. Transfer ownership of the RegisteredPet to the new owner
        # This removes it from old_owner's My Pets and puts it in new_owner's My Pets
        reg_pet.owner = new_owner
        reg_pet.save()

        # 3. Remove the adoption listing now that the pet has been transferred
        listing.delete()

        messages.success(
            request, 
            f"Adoption finalized! {reg_pet.name} ({reg_pet.registration_number}) has been removed from your pets and officially transferred to {new_owner.username}."
        )
        return redirect('citizen:my_pets_list')

    elif action == 'reject':
        application.status = 'REJECTED'
        application.save()
        messages.info(request, f"Application from {application.applicant.username} was declined.")

    return redirect('citizen:pet_detail', pk=listing.id)


@login_required
def add_comment(request, post_id):
    """Handles the submission of a new comment on a community post."""
    post = get_object_or_404(CommunityPost, id=post_id)
    
    if request.method == 'POST':
        form = PostCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, "Your reply was posted successfully.")
        else:
            messages.error(request, "There was an error posting your reply.")
            
    # Redirect back to the post detail page regardless of success/fail
    return redirect('citizen:post_detail', pk=post.id)