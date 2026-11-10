"""
Servicios auxiliares para gestión de disponibilidad y cálculo de balances de equidad.
"""
from datetime import timedelta
from django.contrib.auth.models import User
from carpooling.models import DisponibilidadDiaria, ViajeVehiculo, AsignacionDia, PerfilUsuario


def asegurar_disponibilidades_semana(lunes):
    """
    Asegura que para los 5 días de la semana (lunes a viernes), todos los usuarios activos
    tengan un registro en DisponibilidadDiaria.
    Si no existe, se crea por defecto:
    - asiste = True
    - puede_conducir = True (si tiene un vehículo activo con plazas > 1)
    """
    usuarios_activos = list(
        User.objects.filter(perfil__activo=True).prefetch_related('vehiculos')
    )
    if not usuarios_activos:
        return

    viernes = lunes + timedelta(days=4)
    # Obtener todas las disponibilidades existentes para esa semana y esos usuarios
    disponibles_existentes = set(
        DisponibilidadDiaria.objects.filter(
            fecha__range=[lunes, viernes],
            usuario__in=usuarios_activos
        ).values_list('usuario_id', 'fecha')
    )

    nuevas_disponibilidades = []
    for user in usuarios_activos:
        tiene_coche_activo = any(v.activo and v.plazas_totales > 1 for v in user.vehiculos.all())
        for i in range(5):
            dia_fecha = lunes + timedelta(days=i)
            if (user.id, dia_fecha) not in disponibles_existentes:
                nuevas_disponibilidades.append(
                    DisponibilidadDiaria(
                        usuario=user,
                        fecha=dia_fecha,
                        asiste=True,
                        puede_conducir=tiene_coche_activo,
                        motivo_ausencia=None,
                        comentarios=''
                    )
                )

    if nuevas_disponibilidades:
        DisponibilidadDiaria.objects.bulk_create(nuevas_disponibilidades, ignore_conflicts=True)


def actualizar_balances_historicos():
    """
    Recalcula los contadores históricos de días conducidos y días como pasajero
    para todos los usuarios activos en base a los planes generados y publicados.
    """
    # Fechas con viajes efectivamente asignados en planes publicados
    fechas_con_viajes = set(
        AsignacionDia.objects.filter(
            plan__publicado=True,
            total_coches__gt=0
        ).values_list('fecha', flat=True)
    )

    for perfil in PerfilUsuario.objects.filter(activo=True).select_related('user'):
        user = perfil.user
        
        # Conducciones reales en planes publicados
        conducidos_planes = ViajeVehiculo.objects.filter(
            conductor=user,
            asignacion_dia__plan__publicado=True
        ).count()

        # Días asistidos en fechas con viajes asignados
        viajados_planes = DisponibilidadDiaria.objects.filter(
            usuario=user,
            asiste=True,
            fecha__in=fechas_con_viajes
        ).count()

        pasajero_planes = max(0, viajados_planes - conducidos_planes)

        perfil.dias_conducidos = perfil.dias_conducidos_base + conducidos_planes
        perfil.dias_pasajero = perfil.dias_pasajero_base + pasajero_planes
        perfil.save(update_fields=['dias_conducidos', 'dias_pasajero'])
