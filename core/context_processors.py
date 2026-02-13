from .models import ThemeConfig, Musician

def hex_to_rgb(hex_value):
    if not hex_value:
        return '0, 0, 0'
    hex_value = hex_value.lstrip('#')
    try:
        rgb = tuple(int(hex_value[i:i+2], 16) for i in (0, 2, 4))
        return f"{rgb[0]}, {rgb[1]}, {rgb[2]}"
    except:
        return '0, 0, 0'

def theme_context(request):
    """Context processor to make theme settings available in all templates"""
    theme = ThemeConfig.get_solo()
    
    theme_rgb = {
        'primary': hex_to_rgb(theme.primary_color),
        'secondary': hex_to_rgb(theme.secondary_color),
        'success': hex_to_rgb(theme.success_color),
        'warning': hex_to_rgb(theme.warning_color),
        'error': hex_to_rgb(theme.error_color),
        'main_bg': hex_to_rgb(theme.main_bg),
    }

    return {
        'theme': theme,
        'theme_rgb': theme_rgb
    }

def user_profile_context(request):
    if request.user.is_authenticated:
        try:
            return {'user_musician': Musician.objects.get(username=request.user.username)}
        except Musician.DoesNotExist:
            return {'user_musician': None}
    return {}
