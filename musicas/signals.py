from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
from allauth.account.signals import user_signed_up
from allauth.socialaccount.models import SocialAccount

@receiver(user_signed_up)
def create_profile_on_google_signup(request, user, **kwargs):
    profile, created = Profile.objects.get_or_create(user=user)
    try:
        social_account = SocialAccount.objects.get(user=user, provider='google')
        photo_url = social_account.extra_data.get('picture')
        if photo_url:
            profile.photo_url = photo_url  # Crie esse campo se quiser salvar a URL
            profile.save()
    except SocialAccount.DoesNotExist:
        pass
