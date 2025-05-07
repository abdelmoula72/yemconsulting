from django import template
from django.templatetags.static import static

register = template.Library()

@register.filter
def dict_get(d, key):
    """
    Permet   {{ my_dict|dict_get:my_key }}   dans les templates
    """
    try:
        return d.get(key)
    except Exception:
        return None




@register.filter(name="default_static")
def default_static(path, static_path):
    """
    Affiche *path* si non‐vide, sinon retourne {% static static_path %}.
    Ex.  {{ img_url|default_static:'default.jpg' }}
    """
    if path:
        return path
    return static(static_path)
