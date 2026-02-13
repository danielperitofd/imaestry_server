import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imaestry.settings')
django.setup()

from core.models import ThemeConfig


def main():
    theme = ThemeConfig.get_solo()
    theme.primary_color = '#6F2682'
    theme.secondary_color = '#36C2D7'
    theme.error_color = '#F25F5C'
    theme.success_color = '#A0D440'
    theme.warning_color = '#FFB337'
    theme.sidebar_bg = '#D2D9E8'
    theme.main_bg = '#FCFCFC'
    theme.gradient_start = '#6F2682'
    theme.gradient_end = '#B469FB'
    theme.card_radius = 12
    theme.save()
    print("Theme palette reset to defaults.")


if __name__ == '__main__':
    main()
