from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from citizen import api_views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from citizen import api_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('citizen/', include('citizen.urls')),
    path('officer/', include('officer.urls')),
    
    # Send users to the citizen portal when they visit the base URL
    path('', RedirectView.as_view(url='/citizen/', permanent=False)),
# --- Mobile API Routes ---
    # Auth & Registration
    path('api/auth/register/', api_views.MobileRegisterUserAPI.as_view(), name='mobile_register'),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='mobile_login'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='mobile_token_refresh'),
    path('api/auth/profile/', api_views.MobileProfileAndPreferencesAPI.as_view(), name='mobile_profile'),
    path('api/auth/change-password/', api_views.MobileChangePasswordAPI.as_view(), name='mobile_change_password'),

    # Pets, Vaccinations, & QR Scanning
    path('api/pets/lookup/', api_views.MobilePetLookupAndCreateAPI.as_view(), name='api_pet_lookup'),
    path('api/pets/<int:pet_id>/vaccinations/', api_views.MobileVaccinationCreateAPI.as_view(), name='api_add_vaccine'),
    path('api/pets/request-access/', api_views.MobileScanRequestListCreateAPI.as_view(), name='api_pet_access'),
    path('api/pets/request-access/<int:request_id>/respond/', api_views.MobileScanRequestRespondAPI.as_view(), name='api_pet_access_respond'),

    # Community Forum
    path('api/community/', api_views.MobileCommunityFeedAPI.as_view(), name='api_community'),
    path('api/community/<int:post_id>/comment/', api_views.MobileCommentCreateAPI.as_view(), name='api_comment_create'),

    # Adoptions
    path('api/adoptions/', api_views.MobileAdoptionFeedAndCreateAPI.as_view(), name='api_adoptions'),
    path('api/adoptions/apply/', api_views.MobileAdoptionApplyAPI.as_view(), name='api_adoption_apply'),
    path('api/adoptions/applications/<int:application_id>/finalize/', api_views.MobileFinalizeAdoptionAPI.as_view(), name='api_adoption_finalize'),

    # Disease Heatmap & Reporting
    path('api/disease-heatmap/', api_views.MobileDiseaseHeatmapAPI.as_view(), name='api_heatmap'),

    # Notifications
    path('api/notifications/', api_views.MobileNotificationListAPI.as_view(), name='api_notifications'),
    path('api/notifications/<int:notif_id>/read/', api_views.MobileNotificationReadAPI.as_view(), name='api_notification_read'),
]