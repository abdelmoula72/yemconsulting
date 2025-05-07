from django import template
from django.forms import BoundField
from django.utils.safestring import SafeString

register = template.Library()

@register.filter
def add_class(value, arg):
    """
    Ajoute une classe CSS à un widget de formulaire
    """
    if isinstance(value, BoundField):
        return value.as_widget(attrs={'class': arg})
    return value

@register.filter
def attr(value, arg):
    """
    Ajoute un attribut HTML à un widget de formulaire
    Format attendu : 'key:value'
    """
    if not isinstance(value, BoundField):
        return value
        
    try:
        key, val = arg.split(':')
        return value.as_widget(attrs={key: val})
    except (ValueError, AttributeError):
        return value 