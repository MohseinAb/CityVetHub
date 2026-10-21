from django.urls import path
from . import views

app_name = 'officer'

urlpatterns = [
    # Dashboard Home
    path('dashboard/', views.officer_dashboard, name='dashboard'),
    
    # Dashboard Actions (These prevent the NoReverseMatch errors)
    path('pet-lookup/', views.pet_lookup, name='pet_lookup'),
    path('verify-cluster/<str:barangay>/<str:disease>/<str:action>/', views.verify_cluster, name='verify_cluster'),
    path('verify-alert/<int:alert_id>/<str:action>/', views.verify_alert, name='verify_alert'),
    
    # System Admin Routes
    path('system-admin/', views.system_admin_dashboard, name='system_admin'),
    path('system-admin/vet/<int:req_id>/<str:action>/', views.verify_vet_application, name='verify_vet'),
    path('system-admin/moderate/<str:item_type>/<int:item_id>/<str:action>/', views.moderate_action, name='moderate_action'),
]