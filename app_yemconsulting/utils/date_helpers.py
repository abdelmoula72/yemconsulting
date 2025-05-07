import datetime as dt
from django.utils import timezone

__all__ = ["business_days_after"]

def business_days_after(n: int, base=None):
    """
    Renvoie la date obtenue en ajoutant *n* jours ouvrables à *base*
    (on saute samedi et dimanche). *base* = aujourd’hui si None.
    """
    d = (base or timezone.localdate())
    added = 0
    while added < n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:      # 0 = lundi … 4 = vendredi
            added += 1
    return d