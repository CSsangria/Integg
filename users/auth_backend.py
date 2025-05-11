from django.contrib.auth.backends import ModelBackend

class AllowInactiveUserBackend(ModelBackend):
    """
    Custom backend that allows inactive users to authenticate.
    """
    def user_can_authenticate(self, user):
        # Allow all users, even if inactive
        return True 