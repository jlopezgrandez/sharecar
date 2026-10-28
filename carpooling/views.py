from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.contrib.auth.models import User
from .models import (
    Vehiculo, DisponibilidadDiaria, PlanSemanal, AsignacionDia, ViajeVehiculo, PerfilUsuario, DIAS_SEMANA_ES
)
from .services.optimizer import OptimizadorCarpooling


def _obtener_lunes_semana(fecha=None):
    if not fecha:
        fecha = timezone.localdate()
    return fecha - timedelta(days=fecha.weekday())


def dashboard_cuadrante(request):
    """
    Vista principal: muestra el cuadrante semanal de coches y pasajeros.
    """
    semana_str = request.GET.get('semana')
    if semana_str:
        try:
            lunes = datetime.strptime(semana_str, '%Y-%m-%d').date()
            lunes = _obtener_lunes_semana(lunes)
        except ValueError:
            lunes = _obtener_lunes_semana()
    else:
        lunes = _obtener_lunes_semana()

    viernes = lunes + timedelta(days=4)
    semana_anterior = lunes - timedelta(days=7)
    semana_siguiente = lunes + timedelta(days=7)

    plan = PlanSemanal.objects.filter(semana_inicio=lunes).first()
    dias_semana = []
    
    for i in range(5):
        dia_fecha = lunes + timedelta(days=i)
        asignacion = None
        if plan:
            asignacion = plan.dias.filter(fecha=dia_fecha).first()
        
        # Obtener viajeros previstos y ausencias para ese día
        disponibilidades = DisponibilidadDiaria.objects.filter(
            fecha=dia_fecha,
            usuario__perfil__activo=True
        ).select_related('usuario', 'usuario__perfil')

        viajeros = [d for d in disponibilidades if d.asiste]
        ausentes = [d for d in disponibilidades if not d.asiste]

        dias_semana.append({
            'fecha': dia_fecha,
            'nombre_dia': DIAS_SEMANA_ES.get(dia_fecha.weekday(), ''),
            'asignacion': asignacion,
            'viajeros': viajeros,
            'ausentes': ausentes,
        })

    # Estadísticas de equidad global
    perfiles = PerfilUsuario.objects.filter(activo=True).select_related('user').order_by('dias_conducidos')

    context = {
        'lunes': lunes,
        'viernes': viernes,
        'semana_anterior': semana_anterior.strftime('%Y-%m-%d'),
        'semana_siguiente': semana_siguiente.strftime('%Y-%m-%d'),
        'plan': plan,
        'dias_semana': dias_semana,
        'perfiles': perfiles,
    }
    return render(request, 'carpooling/dashboard.html', context)


@login_required
def gestionar_disponibilidad(request):
    """
    Permite al usuario conectado marcar los días que asiste y si puede conducir.
    """
    semana_str = request.GET.get('semana')
    if semana_str:
        try:
            lunes = datetime.strptime(semana_str, '%Y-%m-%d').date()
            lunes = _obtener_lunes_semana(lunes)
        except ValueError:
            lunes = _obtener_lunes_semana() + timedelta(days=7) # Por defecto, la próxima semana
    else:
        # Por defecto abre la próxima semana para planificar con antelación
        lunes = _obtener_lunes_semana() + timedelta(days=7)

    viernes = lunes + timedelta(days=4)

    if request.method == 'POST':
        for i in range(5):
            dia_fecha = lunes + timedelta(days=i)
            fecha_str = dia_fecha.strftime('%Y-%m-%d')
            
            asiste = request.POST.get(f'asiste_{fecha_str}') == 'on'
            puede_conducir = request.POST.get(f'puede_conducir_{fecha_str}') == 'on'
            motivo = request.POST.get(f'motivo_{fecha_str}', '')
            comentarios = request.POST.get(f'comentarios_{fecha_str}', '')

            DisponibilidadDiaria.objects.update_or_create(
                usuario=request.user,
                fecha=dia_fecha,
                defaults={
                    'asiste': asiste,
                    'puede_conducir': puede_conducir,
                    'motivo_ausencia': motivo if not asiste else None,
                    'comentarios': comentarios
                }
            )

        messages.success(request, f"¡Disponibilidad guardada correctamente para la semana del {lunes.strftime('%d/%m/%Y')}!")
        return redirect(f"{request.path}?semana={lunes.strftime('%Y-%m-%d')}")

    # Cargar disponibilidades existentes para los 5 días
    dias_form = []
    tiene_vehiculo = request.user.vehiculos.filter(activo=True).exists()

    for i in range(5):
        dia_fecha = lunes + timedelta(days=i)
        disp, _ = DisponibilidadDiaria.objects.get_or_create(
            usuario=request.user,
            fecha=dia_fecha,
            defaults={'asiste': True, 'puede_conducir': tiene_vehiculo}
        )
        dias_form.append({
            'fecha': dia_fecha,
            'fecha_str': dia_fecha.strftime('%Y-%m-%d'),
            'nombre_dia': DIAS_SEMANA_ES.get(dia_fecha.weekday(), ''),
            'disp': disp,
        })

    context = {
        'lunes': lunes,
        'viernes': viernes,
        'dias_form': dias_form,
        'tiene_vehiculo': tiene_vehiculo,
        'motivos_ausencia': DisponibilidadDiaria.MOTIVOS_AUSENCIA,
    }
    return render(request, 'carpooling/disponibilidad.html', context)


@login_required
def generar_plan_semanal(request):
    """
    Ejecuta el motor de optimización para la semana indicada.
    """
    if request.method == 'POST':
        semana_str = request.POST.get('semana')
        if semana_str:
            lunes = datetime.strptime(semana_str, '%Y-%m-%d').date()
            lunes = _obtener_lunes_semana(lunes)
        else:
            lunes = _obtener_lunes_semana()

        viernes = lunes + timedelta(days=4)

        # Crear o recuperar el PlanSemanal
        plan, _ = PlanSemanal.objects.get_or_create(
            semana_inicio=lunes,
            defaults={'semana_fin': viernes, 'publicado': True}
        )
        plan.semana_fin = viernes
        plan.publicado = True
        plan.save()

        # Ejecutar optimizador
        optimizador = OptimizadorCarpooling(plan)
        resultado = optimizador.ejecutar_planificacion_semanal()

        messages.success(
            request,
            f"Plan semanal generado con éxito para la semana del {lunes.strftime('%d/%m/%Y')}. Se optimizaron {resultado['dias_optimizados']} días."
        )
        return redirect(f"/?semana={lunes.strftime('%Y-%m-%d')}")

    return redirect('/')


@login_required
def mis_vehiculos(request):
    """
    Gestión sencilla de vehículos del usuario logueado.
    """
    if request.method == 'POST':
        vehiculo_id = request.POST.get('vehiculo_id')
        marca_modelo = request.POST.get('marca_modelo')
        matricula = request.POST.get('matricula', '')
        plazas = int(request.POST.get('plazas_totales', 5))
        activo = request.POST.get('activo') == 'on'

        if vehiculo_id:
            vehiculo = get_object_or_404(Vehiculo, id=vehiculo_id, propietario=request.user)
            vehiculo.marca_modelo = marca_modelo
            vehiculo.matricula = matricula
            vehiculo.plazas_totales = plazas
            vehiculo.activo = activo
            vehiculo.save()
            messages.success(request, "Vehículo actualizado correctamente.")
        else:
            Vehiculo.objects.create(
                propietario=request.user,
                marca_modelo=marca_modelo,
                matricula=matricula,
                plazas_totales=plazas,
                activo=activo
            )
            messages.success(request, "Vehículo registrado correctamente.")

        return redirect('mis_vehiculos')

    vehiculos = request.user.vehiculos.all()
    return render(request, 'carpooling/mis_vehiculos.html', {'vehiculos': vehiculos})
