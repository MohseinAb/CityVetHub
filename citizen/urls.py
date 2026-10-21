from django.urls import path
from . import views

app_name = 'citizen'

urlpatterns = [
    # Citizen Home & Forum
    path('', views.citizen_home, name='home'),
    path('community/', views.community_feed, name='community_feed'),
    path('community/new/', views.create_post, name='create_post'),
    path('community/<int:pk>/', views.post_detail, name='post_detail'),

    # Pet Adoption
    path('adoption/', views.pet_list, name='pet_list'),
    path('adoption/new/', views.list_pet_for_adoption, name='list_pet'),
    path('adoption/<int:pk>/', views.pet_detail, name='pet_detail'),

    # Pet Registry & Passport
    path('pets/', views.my_pets_list, name='my_pets_list'),
    path('pets/register/', views.register_pet, name='register_pet'),
    path('pets/<int:pk>/', views.pet_passport, name='pet_passport'),
    path('pets/scan/<str:reg_num>/', views.scan_pet_qr, name='scan_pet_qr'),
    path('pets/requests/<int:request_id>/<str:action>/', views.manage_access_request, name='manage_access_request'),

    # Disease Surveillance & Alerts
    path('alerts/', views.disease_alerts_list, name='disease_alerts'),
    path('alerts/report/', views.report_disease_incident, name='report_disease'),
    path('alerts/<int:pk>/', views.disease_alert_detail, name='disease_alert_detail'),

    # OP Post Controls
    path('community/post/<int:post_id>/edit/', views.edit_community_post, name='edit_community_post'),
    path('community/post/<int:post_id>/delete/', views.delete_community_post, name='delete_community_post'),

    # OP Adoption Controls & Ownership Transfer
    path('adoption/<int:pet_id>/edit/', views.edit_adoption_listing, name='edit_adoption_listing'),
    path('adoption/<int:pet_id>/delete/', views.delete_adoption_listing, name='delete_adoption_listing'),
    path('adoption/application/<int:app_id>/<str:action>/', views.finalize_adoption, name='finalize_adoption'),
    path('disease-watch/', views.disease_alerts, name='disease_alerts'),
    path('disease/report/', views.report_disease, name='report_disease'),

    # Community Post Routes
    path('community/post/<int:post_id>/edit/', views.edit_community_post, name='edit_community_post'),
    path('community/post/<int:post_id>/delete/', views.delete_community_post, name='delete_community_post'),
    
    # Add this line for the comment submission
    path('community/post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
]