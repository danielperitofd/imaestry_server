import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imaestry.settings')
django.setup()

from core.models import ThemeConfig

# Get or create the theme config
theme = ThemeConfig.get_solo()

print("=== Configuração Atual do Tema ===")
print(f"Primary Color: {theme.primary_color}")
print(f"Secondary Color: {theme.secondary_color}")
print(f"Error Color: {theme.error_color}")
print(f"Success Color: {theme.success_color}")
print(f"Warning Color: {theme.warning_color}")
print(f"Sidebar BG: {theme.sidebar_bg}")
print(f"Main BG: {theme.main_bg}")
print(f"Gradient Start: {theme.gradient_start}")
print(f"Gradient End: {theme.gradient_end}")

# Check if colors match the expected defaults
expected = {
    'primary_color': '#6F2682',
    'secondary_color': '#36C2D7',
    'error_color': '#F25F5C',
    'success_color': '#A0D440',
    'warning_color': '#FFB337',
    'sidebar_bg': '#D2D9E8',
    'main_bg': '#FCFCFC',
    'gradient_start': '#6F2682',
    'gradient_end': '#B469FB',
}

print("\n=== Verificação ===")
all_correct = True
for key, expected_value in expected.items():
    current_value = getattr(theme, key)
    if current_value.upper() != expected_value.upper():
        print(f"❌ {key}: esperado {expected_value}, atual {current_value}")
        all_correct = False
    else:
        print(f"✅ {key}: {current_value}")

if not all_correct:
    print("\n⚠️  Algumas cores não estão corretas. Resetando para padrão...")
    theme.primary_color = '#6F2682'
    theme.secondary_color = '#36C2D7'
    theme.error_color = '#F25F5C'
    theme.success_color = '#A0D440'
    theme.warning_color = '#FFB337'
    theme.sidebar_bg = '#D2D9E8'
    theme.main_bg = '#FCFCFC'
    theme.gradient_start = '#6F2682'
    theme.gradient_end = '#B469FB'
    theme.save()
    print("✅ Tema resetado com sucesso!")
else:
    print("\n✅ Todas as cores estão corretas!")
