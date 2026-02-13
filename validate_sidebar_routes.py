import os
import django
from django.urls import reverse, NoReverseMatch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imaestry.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client


def ensure_test_superuser():
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username="testadmin",
        defaults={
            "email": "test@example.com",
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if created:
        user.set_password("testpass123")
        user.save()
    else:
        # Guarantee staff/superuser in case it was modified
        if not user.is_superuser or not user.is_staff:
            user.is_superuser = True
            user.is_staff = True
            user.save()
    return user


def main():
    user = ensure_test_superuser()
    client = Client()
    client.force_login(user)

    route_names = [
        'home',
        'repertorio',
        'create_team',
        'cadastros',
        'configuracoes',
        'settings_users',
        'add_music_search',
        'import_spotify',
        'join_team',
    ]

    print("--- Validating sidebar routes (GET) ---")
    for name in route_names:
        try:
            url = reverse(name)
        except NoReverseMatch:
            print(f"[MISSING] {name}: NoReverseMatch")
            continue

        resp = client.get(url)
        print(f"[{resp.status_code}] {name} -> {url}")


if __name__ == "__main__":
    main()
