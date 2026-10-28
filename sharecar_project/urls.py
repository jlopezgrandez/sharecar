"""
URL configuration for sharecar_project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('carpooling.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]

admin.site.site_header = "ShareCar - Administración de Coche Compartido"
admin.site.site_title = "ShareCar Admin"
admin.site.index_title = "Gestión de Vehículos y Rutas Semanales"
