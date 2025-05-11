from django.shortcuts import redirect
from django.urls import reverse

class DeactivatedUserLockMiddleware:
    """
    Redirect deactivated users to the submit appeal page, except for allowed URLs.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check for authenticated, inactive users
        if request.user.is_authenticated and not request.user.is_active:
            allowed_paths = [
                reverse('submit-appeal'),
                reverse('logout'),
            ]
            # Allow admin and staff users to access everything
            if request.user.is_staff:
                return self.get_response(request)
            # If not already on allowed paths, redirect
            if request.path not in allowed_paths:
                return redirect('submit-appeal')
        return self.get_response(request) 