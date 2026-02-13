import os
import django
from django.conf import settings
from django.template.loader import render_to_string

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imaestry.settings')
django.setup()

from django.test import RequestFactory
from core.models import ThemeConfig
from core.context_processors import theme_context

def debug_theme():
    print("--- Debugging Theme ---")
    
    # 1. Check DB
    try:
        theme = ThemeConfig.get_solo()
        print(f"DB Primary Color: '{theme.primary_color}'")
        print(f"DB Secondary Color: '{theme.secondary_color}'")
    except Exception as e:
        print(f"DB Error: {e}")
        return

    # 2. Check Context Processor
    factory = RequestFactory()
    request = factory.get('/')
    request.user = type('User', (object,), {'is_authenticated': True, 'username': 'admin', 'id': 1})()
    
    try:
        ctx = theme_context(request)
        print(f"Context 'theme_rgb': {ctx.get('theme_rgb')}")
    except Exception as e:
        print(f"Context Processor Error: {e}")
        return

    # 3. Check Render
    try:
        rendered = render_to_string('core/base.html', request=request)
        # Extract the style block
        import re
        match = re.search(r':root\s*\{(.*?)\}', rendered, re.DOTALL)
        if match:
            print("\n--- Rendered :root CSS ---")
            print(match.group(1).strip())
        else:
            print("\nERROR: No :root block found in rendered template.")
            
    except Exception as e:
        print(f"Render Error: {e}")

if __name__ == "__main__":
    debug_theme()
