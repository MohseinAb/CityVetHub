from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def cvo_officer_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if getattr(request.user, 'role', '') == 'VET_OFFICER' or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Access restricted to City Veterinary Officers.")
        return redirect('citizen:home')
    return _wrapped_view