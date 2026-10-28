from django.contrib import admin
from .models import PerfilUsuario, Vehiculo, DisponibilidadDiaria, PlanSemanal, AsignacionDia, ViajeVehiculo


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('user', 'telefono', 'activo', 'dias_conducidos', 'dias_pasajero', 'ratio_aportacion_display')
    list_filter = ('activo',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'telefono')

    @admin.display(description="Ratio de Aportación")
    def ratio_aportacion_display(self, obj):
        return f"{obj.ratio_aportacion * 100:.1f}%"


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('marca_modelo', 'propietario', 'matricula', 'plazas_totales', 'plazas_pasajeros', 'activo')
    list_filter = ('activo', 'plazas_totales')
    search_fields = ('marca_modelo', 'matricula', 'propietario__username', 'propietario__first_name')


@admin.register(DisponibilidadDiaria)
class DisponibilidadDiariaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha', 'asiste', 'puede_conducir', 'motivo_ausencia', 'comentarios')
    list_filter = ('fecha', 'asiste', 'puede_conducir', 'motivo_ausencia')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')
    date_hierarchy = 'fecha'


class ViajeVehiculoInline(admin.TabularInline):
    model = ViajeVehiculo
    extra = 0
    filter_horizontal = ('pasajeros',)


class AsignacionDiaInline(admin.StackedInline):
    model = AsignacionDia
    extra = 0


@admin.register(PlanSemanal)
class PlanSemanalAdmin(admin.ModelAdmin):
    list_display = ('semana_inicio', 'semana_fin', 'publicado', 'fecha_generacion')
    list_filter = ('publicado',)
    date_hierarchy = 'semana_inicio'


@admin.register(AsignacionDia)
class AsignacionDiaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'plan', 'total_viajeros', 'total_coches')
    list_filter = ('fecha',)
    inlines = [ViajeVehiculoInline]


@admin.register(ViajeVehiculo)
class ViajeVehiculoAdmin(admin.ModelAdmin):
    list_display = ('asignacion_dia', 'conductor', 'vehiculo', 'ocupacion_actual', 'plazas_libres')
    filter_horizontal = ('pasajeros',)
    list_filter = ('asignacion_dia__fecha', 'vehiculo')
