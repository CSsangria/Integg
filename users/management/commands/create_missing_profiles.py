from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserProfile


class Command(BaseCommand):
    help = 'Create missing user profiles for existing users'

    def handle(self, *args, **options):
        users_without_profiles = []
        profiles_created = 0

        # Find users without profiles
        for user in User.objects.all():
            try:
                # Try to access the profile
                _ = user.userprofile
            except User.userprofile.RelatedObjectDoesNotExist:
                users_without_profiles.append(user)

        # Create profiles for users that don't have them
        for user in users_without_profiles:
            UserProfile.objects.create(user=user)
            profiles_created += 1
            self.stdout.write(self.style.SUCCESS(f"Created profile for user: {user.username}"))

        if profiles_created > 0:
            self.stdout.write(self.style.SUCCESS(f"Successfully created {profiles_created} missing profiles"))
        else:
            self.stdout.write(self.style.SUCCESS("All users already have profiles")) 