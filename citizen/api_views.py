from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    RegisteredPet, VaccinationRecord, CommunityPost, PostComment, 
    Pet, AdoptionApplication, DiseaseAlert, Notification, 
    PetAccessRequest, PetOwnershipHistory
)
from .serializers import (
    UserRegistrationSerializer, RegisteredPetSerializer, VaccinationRecordSerializer,
    CommunityPostSerializer, PostCommentSerializer, PetAdoptionSerializer, 
    AdoptionApplicationSerializer, DiseaseAlertSerializer, 
    NotificationSerializer, PetAccessRequestSerializer
)

# 1. USER REGISTRATION (SIGN UP)
class MobileRegisterUserAPI(generics.CreateAPIView):
    """POST: Register a new citizen/user account from the mobile app."""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


# 2. PET REGISTRATION, MY PETS, & QR LOOKUP
class MobilePetLookupAndCreateAPI(generics.ListCreateAPIView):
    """GET: Lookup pets (or ?my_pets=true) | POST: Register a new pet."""
    serializer_class = RegisteredPetSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = RegisteredPet.objects.select_related('owner').prefetch_related('vaccinations')
        if self.request.query_params.get('my_pets') == 'true':
            return qs.filter(owner=self.request.user)
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(registration_number__icontains=q) | qs.filter(name__icontains=q)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


# 3. ADD VACCINATION RECORD TO A PET
class MobileVaccinationCreateAPI(generics.CreateAPIView):
    """POST: Add a vaccination record to a specific RegisteredPet."""
    serializer_class = VaccinationRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        pet = get_object_or_404(RegisteredPet, id=self.kwargs['pet_id'])
        serializer.save(pet=pet)


# 4. QR SCAN ACCESS REQUESTS (CREATE & APPROVE/REJECT)
class MobileScanRequestListCreateAPI(generics.ListCreateAPIView):
    """GET: View scan requests for my pets | POST: Request access after scanning a QR code."""
    serializer_class = PetAccessRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PetAccessRequest.objects.filter(pet__owner=self.request.user).select_related('pet', 'requester')

    def perform_create(self, serializer):
        serializer.save(requester=self.request.user)


class MobileScanRequestRespondAPI(APIView):
    """POST: Pet owner approves or rejects a QR scan access request."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, request_id):
        scan_req = get_object_or_404(PetAccessRequest, id=request_id, pet__owner=request.user)
        new_status = request.data.get('status') # 'APPROVED' or 'REJECTED'
        if new_status not in ['APPROVED', 'REJECTED']:
            return Response({'error': 'Invalid status. Use APPROVED or REJECTED.'}, status=status.HTTP_400_BAD_REQUEST)
        
        scan_req.status = new_status
        scan_req.reviewed_at = timezone.now()
        scan_req.save()
        return Response(PetAccessRequestSerializer(scan_req).data)


# 5. COMMUNITY POSTS & COMMENTS
class MobileCommunityFeedAPI(generics.ListCreateAPIView):
    """GET: Read posts | POST: Create a new post."""
    queryset = CommunityPost.objects.select_related('author').prefetch_related('comments__author')
    serializer_class = CommunityPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MobileCommentCreateAPI(generics.CreateAPIView):
    """POST: Add a comment to a specific community post."""
    serializer_class = PostCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        post = get_object_or_404(CommunityPost, id=self.kwargs['post_id'])
        serializer.save(author=self.request.user, post=post)
        if post.author != self.request.user:
            Notification.objects.create(
                recipient=post.author,
                notif_type='COMMENT',
                message=f"{self.request.user.username} commented on your post '{post.title}'."
            )


# 6. ADOPTIONS: LISTING A PET, APPLYING, & FINALIZING TRANSFER
class MobileAdoptionFeedAndCreateAPI(generics.ListCreateAPIView):
    """GET: View available pets (or ?matched_only=true) | POST: List a pet for adoption."""
    serializer_class = PetAdoptionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Pet.objects.filter(status='AVAILABLE').select_related('registered_pet__owner', 'listed_by')
        if self.request.query_params.get('matched_only') == 'true' and self.request.user.is_authenticated:
            user = self.request.user
            prefs = getattr(user, 'preferences', user)
            pref_species = getattr(prefs, 'preferred_species', None)
            pref_gender = getattr(prefs, 'preferred_gender', None)
            pref_barangay = getattr(prefs, 'preferred_barangay', None)
            if pref_species and pref_species != 'ANY':
                qs = qs.filter(registered_pet__species=pref_species)
            if pref_gender and pref_gender != 'ANY':
                qs = qs.filter(registered_pet__gender=pref_gender)
            if pref_barangay and pref_barangay != 'ANY':
                qs = qs.filter(registered_pet__barangay=pref_barangay)
        return qs

    def perform_create(self, serializer):
        serializer.save(listed_by=self.request.user, status='AVAILABLE')


class MobileAdoptionApplyAPI(generics.ListCreateAPIView):
    """GET: View applications for my listed pets | POST: Apply to adopt a pet."""
    serializer_class = AdoptionApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AdoptionApplication.objects.filter(pet__listed_by=self.request.user).select_related('pet__registered_pet', 'applicant')

    def perform_create(self, serializer):
        app = serializer.save(applicant=self.request.user)
        Notification.objects.create(
            recipient=app.pet.listed_by,
            notif_type='ADOPTION',
            message=f"{self.request.user.username} applied to adopt {app.pet.registered_pet.name}."
        )


class MobileFinalizeAdoptionAPI(APIView):
    """POST: Approve or Reject an adoption application & auto-transfer ownership."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, application_id):
        app = get_object_or_404(AdoptionApplication, id=application_id, pet__listed_by=request.user)
        decision = request.data.get('status') # 'APPROVED' or 'REJECTED'

        if decision == 'APPROVED':
            app.status = 'APPROVED'
            app.save()

            # Mark adoption listing as ADOPTED
            pet_listing = app.pet
            pet_listing.status = 'ADOPTED'
            pet_listing.save()

            # Reject other pending applications for this same pet
            AdoptionApplication.objects.filter(pet=pet_listing, status='PENDING').exclude(id=app.id).update(status='REJECTED')

            # Transfer ownership of the RegisteredPet and log history
            reg_pet = pet_listing.registered_pet
            prev_owner = reg_pet.owner
            reg_pet.owner = app.applicant
            reg_pet.save()

            PetOwnershipHistory.objects.create(
                pet=reg_pet,
                previous_owner=prev_owner,
                new_owner=app.applicant,
                transfer_type='ADOPTION',
                notes=f"Approved via Mobile App (Application #{app.id})"
            )

            Notification.objects.create(
                recipient=app.applicant,
                notif_type='ADOPTION',
                message=f"Congratulations! Your adoption of {reg_pet.name} has been approved!"
            )
            return Response({'status': 'Adoption finalized and pet ownership transferred.'})

        elif decision == 'REJECTED':
            app.status = 'REJECTED'
            app.save()
            Notification.objects.create(
                recipient=app.applicant,
                notif_type='ADOPTION',
                message=f"Your adoption application for {app.pet.registered_pet.name} was declined."
            )
            return Response({'status': 'Application rejected.'})

        return Response({'error': 'Invalid status. Send APPROVED or REJECTED.'}, status=status.HTTP_400_BAD_REQUEST)


# 7. DISEASE HEATMAP & REPORTING
class MobileDiseaseHeatmapAPI(generics.ListCreateAPIView):
    """GET: Verified alerts for map (?all=true for all reports) | POST: Report a disease."""
    serializer_class = DiseaseAlertSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = DiseaseAlert.objects.select_related('reporter')
        if self.request.query_params.get('all') == 'true':
            return qs
        return qs.filter(status='VERIFIED')

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user, status='UNVERIFIED')


# 8. NOTIFICATIONS (LIST & MARK AS READ)
class MobileNotificationListAPI(generics.ListAPIView):
    """GET: Notifications for logged-in user."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class MobileNotificationReadAPI(APIView):
    """POST: Mark a notification as read."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notif_id):
        notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
        notif.is_read = True
        notif.save()
        return Response({'status': 'Notification marked as read.'})

class MobileProfileAndPreferencesAPI(generics.RetrieveUpdateAPIView):
    """
    GET: Fetch logged-in user's profile & adoption preferences.
    PATCH / PUT: Update profile details (name, email, barangay, phone) & preferences.
    """
    serializer_class = UserProfileAndPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user


# 10. CHANGE PASSWORD
class MobileChangePasswordAPI(APIView):
    """POST: Verify old_password and set new_password."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'old_password': ['Wrong current password.']}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'status': 'Password updated successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)