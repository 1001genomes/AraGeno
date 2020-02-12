"""
Production settings
"""
# Load defaults in order to then add/override with dev-only settings
import os
from .defaults import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db', 'db.sqlite3'),
    }
}
ADMINS = [ tuple(admin.split(',')) for admin in os.environ['ADMINS'].split()]
EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = os.environ.get("EMAIL_PORT", 25)
EMAIL_HOST_USER = os.environ["EMAIL_USER"]
