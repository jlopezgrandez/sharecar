"""
Servicios auxiliares para gestión de disponibilidad y cálculo de balances de equidad.
"""
from django.contrib.auth.models import User
from carpooling.models import DisponibilidadDiaria, ViajeVehiculo, AsignacionDia, PerfilUsuario


def obtener_usuarios_activos():
    """
    Obtiene todos los usuarios activos del sistema para el carpooling.
    Garantiza que todos tengan su PerfilUsuario creado con activo=True.
    Si existen usuarios trabajadores además del admin, excluye la cuenta puramente de gestión 'admin'.
    """
    todos_activos = list(
        User.objects.filter(is_active=True)
        .select_related('perfil')
        .prefetch_related('vehiculos')
    )

    # Si hay compañeros además del admin, excluimos el usuario técnico 'admin'
    if len(todos_activos) > 1:
        usuarios_candidatos = [u for u in todos_activos if u.username != 'admin']
    else:
        usuarios_candidatos = todos_activos

    activos = []
    for u in usuarios_candidatos:
        try:
            perfil = u.perfil
        except (PerfilUsuario.DoesNotExist, AttributeError):
            perfil, _ = PerfilUsuario.objects.get_or_create(user=u, defaults={'activo': True})
            u.perfil = perfil

        if perfil.activo:
            activos.append(u)

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
        perfil = user.perfil

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
