from allauth.socialaccount.models import SocialAccount

def user_profile_context(request):
    if request.user.is_authenticated:
        photo_url = None

        # Tenta pegar do Profile
        if hasattr(request.user, "profile") and request.user.profile.photo:
            photo_url = request.user.profile.photo.url
        else:
            # Tenta pegar do Google
            try:
                social = SocialAccount.objects.get(user=request.user, provider='google')
                photo_url = social.extra_data.get('picture')
            except SocialAccount.DoesNotExist:
                photo_url = None

        return {
            "photo": photo_url or "/static/musicas/images/avatar_padrao_man.jpg",
            "name": request.user.get_full_name() or request.user.username,
            "email": request.user.email,
        }
    return {}
