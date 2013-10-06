try:
    from django.db.models.constants import LOOKUP_SEP
except ImportError:
    # To support Django 1.4 we move to location where Django 1.5+ has constants
    import sys
    from django.db.models.sql import constants
    import django.db.models
    django.db.models.constants = constants
    sys.modules['django.db.models.constants'] = django.db.models.constants
