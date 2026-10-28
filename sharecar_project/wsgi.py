"""
WSGI config for sharecar_project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sharecar_project.settings')

application = get_wsgi_application()
