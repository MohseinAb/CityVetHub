from django.contrib import admin
from .models import CustomUser, VetVerificationRequest

admin.site.register(CustomUser)
admin.site.register(VetVerificationRequest)