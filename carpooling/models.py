from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


DIAS_SEMANA_ES = {
    0: 'Lunes',
    1: 'Martes',
    2: 'Miércoles',
    3: 'Jueves',
    4: 'Viernes',
    5: 'Sábado',
    6: 'Domingo',
}


class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    activo = models.BooleanField(default=True, verbose_name="Participa activamente")
    
    # Balance histórico para algoritmo de equidad
    dias_conducidos = models.PositiveIntegerField(default=0, verbose_name="Días que ha conducido")
    dias_pasajero = models.PositiveIntegerField(default=0, verbose_name="Días como pasajero")

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

    @property
    def dias_totales(self):
        return self.dias_conducidos + self.dias_pasajero

    @property
    def ratio_aportacion(self):
        """Ratio entre días conducidos y días totales viajados."""
        if self.dias_totales == 0:
            return 0.0
        return round(self.dias_conducidos / self.dias_totales, 3)

    @property
    def vehiculo_activo(self):
        return self.user.vehiculos.filter(activo=True).first()


class Vehiculo(models.Model):
    propietario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehiculos', verbose_name="Propietario")
    marca_modelo = models.CharField(max_length=100, verbose_name="Marca y Modelo")
    matricula = models.CharField(max_length=20, blank=True, null=True, verbose_name="Matrícula")
    plazas_totales = models.PositiveIntegerField(
        default=5,
        verbose_name="Plazas totales (incluyendo conductor)",
        help_text="Capacidad total del vehículo (ej: 5 plazas)"
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Disponible para rutas",
        help_text="Desmarcar si el coche está en el taller o no disponible temporalmente"
    )

    class Meta:
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"

    def __str__(self):
        return f"{self.marca_modelo} ({self.plazas_totales} plazas) - {self.propietario.get_full_name() or self.propietario.username}"

    @property
    def plazas_pasajeros(self):
        """Plazas libres para pasajeros (plazas totales menos el conductor)."""
        return max(0, self.plazas_totales - 1)


class DisponibilidadDiaria(models.Model):
    MOTIVOS_AUSENCIA = [
        ('TELETRABAJO', 'Teletrabajo'),
        ('VACACIONES', 'Vacaciones'),
        ('MEDICO_BAJA', 'Enfermedad / Cita médica'),
        ('ASUNTOS_PROPIOS', 'Asuntos propios'),
        ('OTRO', 'Otro motivo'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disponibilidades', verbose_name="Usuario")
    fecha = models.DateField(verbose_name="Fecha")
    asiste = models.BooleanField(default=True, verbose_name="¿Viaja este día?")
    puede_conducir = models.BooleanField(
        default=True,
        verbose_name="¿Puede aportar su coche si hace falta?",
        help_text="Marcar 'No' si el usuario viaja pero no puede conducir (lesión, coche no disponible, etc.)"
    )
    motivo_ausencia = models.CharField(
        max_length=20,
        choices=MOTIVOS_AUSENCIA,
        blank=True,
        null=True,
        verbose_name="Motivo si no asiste"
    )
    comentarios = models.CharField(max_length=255, blank=True, verbose_name="Notas adicionales")

    class Meta:
        verbose_name = "Disponibilidad Diaria"
        verbose_name_plural = "Disponibilidades Diarias"
        unique_together = ('usuario', 'fecha')
        ordering = ['fecha', 'usuario__username']

    def __str__(self):
        estado = "Asiste" if self.asiste else f"No asiste ({self.get_motivo_ausencia_display() or 'Sin motivo'})"
        return f"{self.usuario.username} - {self.fecha.strftime('%d/%m/%Y')}: {estado}"


class PlanSemanal(models.Model):
    semana_inicio = models.DateField(verbose_name="Lunes de la semana")
    semana_fin = models.DateField(verbose_name="Viernes/Fin de semana")
    fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name="Generado el")
    publicado = models.BooleanField(default=True, verbose_name="Publicado y visible para los usuarios")
    notas = models.TextField(blank=True, verbose_name="Observaciones generales")

    class Meta:
        verbose_name = "Plan Semanal"
        verbose_name_plural = "Planes Semanales"
        ordering = ['-semana_inicio']

    def __str__(self):
        return f"Semana del {self.semana_inicio.strftime('%d/%m/%Y')} al {self.semana_fin.strftime('%d/%m/%Y')}"


class AsignacionDia(models.Model):
    plan = models.ForeignKey(PlanSemanal, on_delete=models.CASCADE, related_name='dias', verbose_name="Plan Semanal")
    fecha = models.DateField(verbose_name="Fecha")
    total_viajeros = models.PositiveIntegerField(default=0, verbose_name="Total personas que viajan")
    total_coches = models.PositiveIntegerField(default=0, verbose_name="Total coches asignados")

    class Meta:
        verbose_name = "Asignación del Día"
        verbose_name_plural = "Asignaciones Diarias"
        ordering = ['fecha']
        unique_together = ('plan', 'fecha')

    def __str__(self):
        nombre_dia = DIAS_SEMANA_ES.get(self.fecha.weekday(), '')
        return f"{nombre_dia} {self.fecha.strftime('%d/%m/%Y')}: {self.total_viajeros} viajeros en {self.total_coches} coches"


class ViajeVehiculo(models.Model):
    asignacion_dia = models.ForeignKey(AsignacionDia, on_delete=models.CASCADE, related_name='viajes_vehiculo', verbose_name="Día")
    conductor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viajes_como_conductor', verbose_name="Conductor")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, verbose_name="Vehículo utilizado")
    pasajeros = models.ManyToManyField(User, related_name='viajes_como_pasajero', blank=True, verbose_name="Pasajeros")

    class Meta:
        verbose_name = "Coche asignado en ruta"
        verbose_name_plural = "Coches asignados en ruta"

    def __str__(self):
        return f"Coche de {self.conductor.get_full_name() or self.conductor.username} ({self.vehiculo.marca_modelo}) - {self.asignacion_dia.fecha.strftime('%d/%m/%Y')}"

    @property
    def ocupacion_actual(self):
        # 1 conductor + cantidad de pasajeros
        return 1 + self.pasajeros.count()

    @property
    def plazas_libres(self):
        return max(0, self.vehiculo.plazas_totales - self.ocupacion_actual)
