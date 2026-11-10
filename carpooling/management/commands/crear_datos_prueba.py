"""
Comando para resetear la base de datos con un conjunto limpio y completo de datos de prueba.
Uso: python manage.py crear_datos_prueba
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from carpooling.models import PerfilUsuario, Vehiculo, DisponibilidadDiaria, PlanSemanal, AsignacionDia, ViajeVehiculo
from carpooling.services.optimizer import OptimizadorCarpooling
from carpooling.services.disponibilidad import actualizar_balances_historicos


class Command(BaseCommand):
    help = 'Limpia la base de datos y crea un entorno de prueba 100% operativo con usuarios, coches y cuadrantes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=== Limpiando planes, viajes y disponibilidades previas ==="))
        ViajeVehiculo.objects.all().delete()
        AsignacionDia.objects.all().delete()
        PlanSemanal.objects.all().delete()
        DisponibilidadDiaria.objects.all().delete()
        Vehiculo.objects.all().delete()

        # 1. Superusuario administrador
        admin_user, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@ejemplo.com', 'is_staff': True, 'is_superuser': True})
        admin_user.set_password('admin123')
        admin_user.first_name = "Administrador"
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        perfil_admin, _ = PerfilUsuario.objects.get_or_create(user=admin_user)
        perfil_admin.activo = False  # El admin no viaja en las rutas diarias de compañeros
        perfil_admin.save()
        self.stdout.write(self.style.SUCCESS("Usuario admin configurado: admin / admin123"))

        # 2. Lista de compañeros reales/de prueba con sus vehículos y plazas
        usuarios_data = [
            ('carlos', 'Carlos', 'Gómez', 'Peugeot 308', 5, True, 2, 4),
            ('ana', 'Ana', 'Martínez', 'Toyota Corolla', 5, True, 1, 5),
            ('david', 'David', 'López', 'Seat Ibiza', 4, True, 3, 3),
            ('elena', 'Elena', 'Ruiz', 'Ford Fiesta', 4, True, 1, 4),
            ('fernando', 'Fernando', 'Sanz', 'Volkswagen Polo', 4, True, 2, 3),
            ('lucia', 'Lucía', 'Navarro', None, 0, False, 0, 6),
            ('miguel', 'Miguel', 'Torres', 'Renault Megane', 5, False, 2, 4), # Coche temporalmente en taller
            ('sara', 'Sara', 'Blanco', None, 0, False, 0, 5),
            ('pablo', 'Pablo', 'Vargas', 'Hyundai Tucson', 5, True, 0, 5),
        ]

        usuarios_creados = []
        for username, fname, lname, coche, plazas, coche_activo, cond, pas in usuarios_data:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'first_name': fname, 'last_name': lname, 'email': f"{username}@empresa.com"}
            )
            user.first_name = fname
            user.last_name = lname
            user.is_active = True
            user.set_password('demo1234')
            user.save()

            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            perfil.dias_conducidos_base = cond
            perfil.dias_pasajero_base = pas
            perfil.dias_conducidos = cond
            perfil.dias_pasajero = pas
            perfil.activo = True
            perfil.save()

            if coche:
                Vehiculo.objects.create(
                    propietario=user,
                    marca_modelo=coche,
                    plazas_totales=plazas,
                    activo=coche_activo
                )

            usuarios_creados.append(user)

        self.stdout.write(self.style.SUCCESS(f"{len(usuarios_creados)} compañeros y sus coches registrados con éxito."))

        hoy = timezone.localdate()
        lunes_actual = hoy - timedelta(days=hoy.weekday())
        viernes_actual = lunes_actual + timedelta(days=4)

        # 3. Notificación de ausencia de ejemplo: Elena teletrabaja el miércoles de esta semana
        elena_user = User.objects.get(username='elena')
        miercoles_actual = lunes_actual + timedelta(days=2)
        DisponibilidadDiaria.objects.create(
            usuario=elena_user,
            fecha=miercoles_actual,
            asiste=False,
            motivo_ausencia='TELETRABAJO',
            comentarios='Teletrabajo semanal acordado'
        )

        # 4. Generar y optimizar automáticamente el plan para ESTA semana
        plan_actual, _ = PlanSemanal.objects.get_or_create(
            semana_inicio=lunes_actual,
            defaults={'semana_fin': viernes_actual, 'publicado': True}
        )
        plan_actual.semana_fin = viernes_actual
        plan_actual.publicado = True
        plan_actual.save()

        opt1 = OptimizadorCarpooling(plan_actual)
        res1 = opt1.ejecutar_planificacion_semanal()
        self.stdout.write(self.style.SUCCESS(
            f"Plan de ESTA semana ({lunes_actual.strftime('%d/%m/%Y')} al {viernes_actual.strftime('%d/%m/%Y')}) optimizado con éxito."
        ))

        # 5. Generar y optimizar automáticamente el plan para la PRÓXIMA semana
        lunes_proxima = lunes_actual + timedelta(days=7)
        viernes_proxima = lunes_proxima + timedelta(days=4)
        plan_proxima, _ = PlanSemanal.objects.get_or_create(
            semana_inicio=lunes_proxima,
            defaults={'semana_fin': viernes_proxima, 'publicado': True}
        )
        plan_proxima.semana_fin = viernes_proxima
        plan_proxima.publicado = True
        plan_proxima.save()

        opt2 = OptimizadorCarpooling(plan_proxima)
        res2 = opt2.ejecutar_planificacion_semanal()
        self.stdout.write(self.style.SUCCESS(
            f"Plan de la PRÓXIMA semana ({lunes_proxima.strftime('%d/%m/%Y')} al {viernes_proxima.strftime('%d/%m/%Y')}) optimizado con éxito."
        ))

        actualizar_balances_historicos()
        self.stdout.write(self.style.SUCCESS("¡Base de datos restablecida limpiamente y lista para usar!"))
