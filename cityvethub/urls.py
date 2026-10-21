from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView  # Add this import

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('citizen/', include('citizen.urls')),
    path('officer/', include('officer.urls')),
    
    # Send users to the citizen portal when they visit the base URL
    path('', RedirectView.as_view(url='/citizen/', permanent=False)),
]