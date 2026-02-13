
import os
import sys
import django

# Setup Django environment
sys.path.append('c:/_DEVELOPMENT/imaestry')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imaestry.settings')
django.setup()

from core.models import ThemeConfig

def apply_dark_theme():
    config = ThemeConfig.get_solo()
    
    # Palette based on user image request
    # Black/Dark variations
    config.main_bg = '#050510' # Very dark blue/black
    
    # Dark Blue/Purple variations for Sidebar
    config.sidebar_bg = '#150050' # Deep Blue
    
    # Purple/Violet for Accents
    config.primary_color = '#7B2CBF' # Vibrant Purple (visible on dark)
    config.secondary_color = '#3F0071' # Deep Purple
    
    # Gradient
    config.gradient_start = '#3F0071'
    config.gradient_end = '#610094'
    
    # Status colors (keep bright for contrast)
    config.success_color = '#00CC66'
    config.warning_color = '#FFB300'
    config.error_color = '#FF4444'
    
    config.save()
    print("Dark Theme applied successfully!")

if __name__ == '__main__':
    apply_dark_theme()
