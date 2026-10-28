from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_cuadrante, name='dashboard'),
    path('disponibilidad/', views.gestionar_disponibilidad, name='gestionar_disponibilidad'),
    path('plan/generar/', views.generar_plan_semanal, name='generar_plan'),
    path('mis-vehiculos/', views.mis_vehiculos, name='mis_vehiculos'),
]
