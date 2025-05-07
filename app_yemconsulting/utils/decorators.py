from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME

def admin_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Décorateur qui vérifie que l'utilisateur est un administrateur.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_admin,
        login_url='admin:login',
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator 