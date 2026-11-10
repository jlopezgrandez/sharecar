"""
Servicios auxiliares para gestión de disponibilidad y cálculo de balances de equidad.
"""
from django.contrib.auth.models import User
from carpooling.models import DisponibilidadDiaria, ViajeVehiculo, AsignacionDia, PerfilUsuario, Vehiculo


def obtener_usuarios_activos():
    """
    Obtiene todos los usuarios activos del sistema para el carpooling.
    Garantiza que todos tengan su PerfilUsuario creado con activo=True.
    """
    usuarios = list(
        User.objects.filter(is_active=True)
        .prefetch_related('vehiculos')
    )

    activos = []
    for u in usuarios:
        perfil, _ = PerfilUsuario.objects.get_or_create(user=u, defaults={'activo': True})
        if perfil.activo:
            activos.append(u)

    # Si hay varios usuarios y el usuario 'admin' no tiene coche registrado,
    # excluimos 'admin' de los viajeros cotidianos
    if len(activos) > 1:
        admin_sin_coche = [
            u for u in activos 
            if u.username == 'admin' and not u.vehiculos.filter(activo=True).exists()
        ]
        activos = [u for u in activos if u not in admin_sin_coche]

    return activos


def asegurar_disponibilidades_semana(lunes):
    """Función de compatibilidad."""
    pass


def actualizar_balances_historicos():
    """
    Recalcula los contadores históricos de días conducidos y días como pasajero
    para todos los usuarios activos en base a los planes generados y publicados.
    """
    fechas_con_viajes = list(
        AsignacionDia.objects.filter(
            plan__publicado=True,
            total_coches__gt=0
        ).values_list('fecha', flat=True)
    )

    if not fechas_con_viajes:
        return

    # Conjunto de ausencias expresamente notificadas por (usuario_id, fecha)
    ausencias_set = set(
        DisponibilidadDiaria.objects.filter(
            fecha__in=fechas_con_viajes,
            asiste=False
        ).values_list('usuario_id', 'fecha')
    )

    for user in obtener_usuarios_activos():
        perfil, _ = PerfilUsuario.objects.get_or_create(user=user, defaults={'activo': True})

        # Conducciones reales en planes publicados
        conducidos_planes = ViajeVehiculo.objects.filter(
            conductor=user,
            asignacion_dia__plan__publicado=True
        ).count()

        # Días asistidos: todos los días con rutas salvo que haya notificado que no asiste
        dias_viajados = sum(1 for f in fechas_con_viajes if (user.id, f) not in ausencias_set)

        pasajero_planes = max(0, dias_viajados - conducidos_planes)

        perfil.dias_conducidos = perfil.dias_conducidos_base + conducidos_planes
        perfil.dias_pasajero = perfil.dias_pasajero_base + pasajero_planes
        perfil.save(update_fields=['dias_conducidos', 'dias_pasajero'])
