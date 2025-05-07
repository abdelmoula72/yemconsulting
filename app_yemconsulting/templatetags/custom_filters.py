from django import template
from decimal import Decimal
import decimal

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplie la valeur par l'argument"""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return 0

    except (ValueError, TypeError):
        return '' 