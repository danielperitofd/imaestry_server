from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()


@register.simple_tag(takes_context=True)
def profile_edit_url(context):
    request = context.get('request')
    # Prefer the official route with user id; fallback to legacy name.
    try:
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            return reverse('edit_user', args=[request.user.id])
    except NoReverseMatch:
        pass
    try:
        return reverse('profile_edit')
    except NoReverseMatch:
        return '#'
