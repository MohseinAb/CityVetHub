import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.utils import timezone
from citizen.models import DiseaseAlert, RegisteredPet, Pet, VaccinationRecord,CommunityPost
from citizen.forms import VaccinationRecordForm
from accounts.models import CustomUser, VetVerificationRequest

# 44 Barangays Precisely Calibrated to OpenStreetMap Grid
ILIGAN_BARANGAY_COORDS = {
    # Urban Core
    'Poblacion': [8.2275, 124.2385],
    'Saray': [8.2315, 124.2380],
    'Mahayahay': [8.22419, 124.23877],
    'Pala-o': [8.2235, 124.2495],
    'Tubod': [8.2085, 124.2395],
    'Tambacan': [8.2215, 124.2335],
    'Ubaldo Laya': [8.2185, 124.2500],
    
    # Central/North Corridor
    'Tibanga': [8.23933, 124.24196],
    'San Miguel': [8.23854, 124.24904],
    'Villa Verde': [8.23215, 124.24471],
    'Bagong Silang': [8.24136, 124.25152],
    'Del Carmen': [8.23194, 124.25981],
    'Hinaplanon': [8.24648, 124.25990],
    'Upper Hinaplanon': [8.25530, 124.27097],
    'Santiago': [8.25007, 124.24591],
    'San Roque': [8.25712, 124.26346],
    'Santo Rosario': [8.24297, 124.25283],
    
    # Industrial North Coast
    'Santa Filomena': [8.2655, 124.2645],
    'Acmac': [8.2725, 124.2690],
    'Kiwalan': [8.2835, 124.2760],
    'Dalipuga': [8.3120, 124.2640],
    
    # South Corridor (Corrected Tomas Cabili, Suarez, Santa Elena)
    'Tomas Cabili': [8.20963, 124.22221],     # Safely inland, centered on Scions Subdivision
    'Santa Elena': [8.19476, 124.22684],      # Moved West, south of Scions and Bayanihan Village
    'Suarez': [8.1895, 124.2250],           # Aligned near Aries/Madasigon
    'Upper Tominobo': [8.1980, 124.2360],   # Adjusted relative to Santa Elena
    'Ditucalan': [8.1965, 124.2045],
    'Maria Cristina': [8.1750, 124.1880],
    'Buru-un': [8.1880, 124.1740],
    
    # Inland & East (Corrected Tipanoy, Abuno, Puga-an)
    'Tipanoy': [8.2025, 124.2670],          # Snapped directly to LDNICR / Tipanoy label
    'Abuno': [8.1880, 124.2680],            # Aligned south of Tipanoy
    'Luinab': [8.2160, 124.2640],
    'Puga-an': [8.2115, 124.2880],
    'Mandulog': [8.2730, 124.2980],
    
    # Far Upland Hinterlands
    'Bonbonon': [8.2870, 124.3150],
    'Bunawan': [8.3060, 124.3210],
    'Digkilaan': [8.2435, 124.3415],
    'Dulag': [8.1340, 124.3015],
    'Hindang': [8.1620, 124.3310],
    'Kabacsanan': [8.2831, 124.3722],
    'Kalilangan': [8.1450, 124.3520],
    'Lanipao': [8.2678, 124.3411],
    'Mainit': [8.1652, 124.2331],
    'Panoroganan': [8.2150, 124.4120],
    'Rogongon': [8.1520, 124.4250],
}

def is_vet_officer(user):
    return user.is_authenticated and (getattr(user, 'role', '') == 'VET_OFFICER' or user.is_staff)


@user_passes_test(is_vet_officer, login_url='login')
def officer_dashboard(request):
    """CVO Staff Dashboard with dynamic heatmap data payload and report clustering."""
    total_pets = RegisteredPet.objects.count()
    total_adoptions = Pet.objects.filter(status='AVAILABLE').count()
    
    unverified_alerts_raw = DiseaseAlert.objects.filter(status='UNVERIFIED').order_by('-created_at')
    verified_alerts = DiseaseAlert.objects.filter(status='VERIFIED').order_by('-updated_at')

    # Prepare RAW incident data for dynamic JS filtering (All active alerts)
    all_active_alerts = DiseaseAlert.objects.filter(status__in=['UNVERIFIED', 'VERIFIED'])
    incidents_for_map = []
    
    for alert in all_active_alerts:
        if alert.barangay in ILIGAN_BARANGAY_COORDS:
            lat, lng = ILIGAN_BARANGAY_COORDS[alert.barangay]
            incidents_for_map.append({
                'id': alert.id,
                'barangay': alert.barangay,
                'lat': lat,
                'lng': lng,
                'disease': alert.get_disease_display(),
                'status': alert.status,  # 'UNVERIFIED' or 'VERIFIED'
            })

    # Group unverified reports into table clusters by (Barangay, Disease)
    severity_rank = {'LOW': 1, 'MODERATE': 2, 'HIGH': 3, 'CRITICAL': 4}
    pending_clusters = {}
    
    for alert in unverified_alerts_raw:
        key = (alert.barangay, alert.disease)
        if key not in pending_clusters:
            pending_clusters[key] = {
                'barangay': alert.barangay,
                'disease': alert.disease,
                'disease_display': alert.get_disease_display(),
                'count': 0,
                'severity': alert.severity,
                'severity_display': alert.get_severity_display(),
                'reports': []
            }
        
        cluster = pending_clusters[key]
        cluster['reports'].append(alert)
        cluster['count'] += 1
        
        if severity_rank.get(alert.severity, 0) > severity_rank.get(cluster['severity'], 0):
            cluster['severity'] = alert.severity
            cluster['severity_display'] = alert.get_severity_display()
            
    return render(request, 'officer/dashboard.html', {
        'total_pets': total_pets,
        'total_adoptions': total_adoptions,
        'unverified_count': unverified_alerts_raw.count(),
        'pending_clusters': list(pending_clusters.values()),
        'verified_alerts': verified_alerts,
        'incidents_json': json.dumps(incidents_for_map),
    })

@user_passes_test(is_vet_officer, login_url='login')
def verify_disease_cluster(request, barangay, disease, action):
    """Verifies or dismisses all pending reports for a specific pathogen in a barangay."""
    alerts = DiseaseAlert.objects.filter(status='UNVERIFIED', barangay=barangay, disease=disease)
    count = alerts.count()
    
    if action == 'verify':
        alerts.update(status='VERIFIED')
        messages.success(request, f"Verified {count} reports as an official {disease} outbreak in {barangay}.")
    elif action == 'dismiss':
        alerts.delete()
        messages.warning(request, f"Dismissed {count} incident reports for {barangay}.")
        
    return redirect('officer:dashboard')


@user_passes_test(is_vet_officer, login_url='login')
def verify_disease_alert(request, alert_id, action):
    """CVO Officer action to verify, escalate, or resolve a reported outbreak."""
    alert = get_object_or_404(DiseaseAlert, id=alert_id)
    if action == 'verify':
        alert.status = 'VERIFIED'
        messages.success(request, f"Outbreak advisory '{alert.title}' is now VERIFIED by CVO.")
    elif action == 'resolve':
        alert.status = 'RESOLVED'
        messages.info(request, f"Advisory '{alert.title}' has been marked as RESOLVED.")
    elif action == 'delete':
        alert.delete()
        messages.warning(request, "Incident report dismissed and removed.")
        return redirect('officer:dashboard')
    alert.save()
    return redirect('officer:dashboard')


@user_passes_test(is_vet_officer, login_url='login')
def officer_pet_lookup(request):
    """Look up any registered pet by registration tag to inject verified vaccines."""
    query = request.GET.get('q', '').strip()
    pet = None
    vax_form = None

    if query:
        pet = RegisteredPet.objects.filter(
            Q(registration_number__iexact=query) | Q(microchip_or_tag_id__iexact=query)
        ).first()

        if pet and request.method == 'POST':
            vax_form = VaccinationRecordForm(request.POST)
            if vax_form.is_valid():
                record = vax_form.save(commit=False)
                record.pet = pet
                record.administered_by = f"CVO Officer: {request.user.username}"
                record.save()
                messages.success(request, f"Official {record.get_vaccine_name_display()} stamped on {pet.name}!")
                return redirect(f"{request.path}?q={query}")
        else:
            vax_form = VaccinationRecordForm()

    return render(request, 'officer/pet_lookup.html', {
        'query': query,
        'pet': pet,
        'vax_form': vax_form,
    })

def is_cvo_admin(user):
    # Grants access if the user has the CVO_ADMIN role OR is a master superuser
    return user.is_authenticated and (getattr(user, 'role', '') == 'CVO_ADMIN' or user.is_superuser)

@user_passes_test(is_cvo_admin, login_url='login')
def system_admin_dashboard(request):
    """Master Control Panel for CVO Admins."""
    pending_vets = VetVerificationRequest.objects.filter(status='PENDING').order_by('-submitted_at')
    users = CustomUser.objects.all().order_by('-date_joined')[:50]
    flagged_posts = CommunityPost.objects.all().order_by('-created_at')[:20]
    recent_pets = RegisteredPet.objects.all().order_by('-registered_at')[:20]
    
    return render(request, 'officer/admin_dashboard.html', {
        'pending_vets': pending_vets,
        'users': users,
        'posts': flagged_posts,
        'pets': recent_pets,
    })

@user_passes_test(is_cvo_admin, login_url='login')
def verify_vet_application(request, req_id, action):
    vet_req = get_object_or_404(VetVerificationRequest, id=req_id)
    if action == 'approve':
        vet_req.status = 'APPROVED'
        vet_req.reviewed_at = timezone.now()
        vet_req.user.role = 'VET_CLINIC'
        vet_req.user.save()
        vet_req.save()
        messages.success(request, f"Approved {vet_req.user.username} as a Certified Vet.")
    elif action == 'reject':
        vet_req.status = 'REJECTED'
        vet_req.reviewed_at = timezone.now()
        vet_req.save()
        messages.warning(request, f"Rejected application for {vet_req.user.username}.")
    return redirect('officer:system_admin')

@user_passes_test(is_cvo_admin, login_url='login')
def moderate_action(request, item_type, item_id, action):
    """Upgraded generic moderation handler for users, posts, and pets."""
    
    if item_type == 'user':
        user = get_object_or_404(CustomUser, id=item_id)
        # Prevent admins from modifying themselves
        if user == request.user or user.is_superuser:
            messages.error(request, "You cannot modify master superuser accounts.")
            return redirect('officer:system_admin')
            
        if action == 'ban':
            user.is_active = False
            messages.success(request, f"Account {user.username} deactivated.")
        elif action == 'unban':
            user.is_active = True
            messages.success(request, f"Account {user.username} reactivated.")
        elif action == 'promote':
            user.role = 'VET_OFFICER'
            messages.success(request, f"{user.username} promoted to CVO Officer.")
        elif action == 'demote':
            user.role = 'CITIZEN'
            messages.success(request, f"{user.username}'s officer privileges revoked.")
        user.save()
        
    elif item_type == 'post' and action == 'delete':
        post = get_object_or_404(CommunityPost, id=item_id)
        post.delete()
        messages.success(request, "Community post deleted successfully.")
        
    elif item_type == 'pet' and action == 'delete':
        pet = get_object_or_404(RegisteredPet, id=item_id)
        pet.delete()
        messages.success(request, "Pet registry entry removed.")
        
    return redirect('officer:system_admin')

def is_officer_or_admin(user):
    return user.is_authenticated and getattr(user, 'role', '') in ['VET_OFFICER', 'CVO_ADMIN', 'is_superuser']

@user_passes_test(is_officer_or_admin, login_url='login')
def pet_lookup(request):
    """Placeholder for the official pet database search."""
    return HttpResponse("Pet Database Lookup feature is under construction.")

@user_passes_test(is_officer_or_admin, login_url='login')
def verify_cluster(request, barangay, disease, action):
    """Placeholder for approving/dismissing community outbreak clusters."""
    # We will build out this logic next
    return redirect('officer:dashboard')

@user_passes_test(is_officer_or_admin, login_url='login')
def verify_alert(request, alert_id, action):
    """Placeholder for marking active outbreaks as resolved."""
    # We will build out this logic next
    return redirect('officer:dashboard')