"""
Comando para generar datos de prueba y validar el funcionamiento del sistema.
Uso: python manage.py crear_datos_prueba
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from carpooling.models import PerfilUsuario, Vehiculo, DisponibilidadDiaria, PlanSemanal
from carpooling.services.optimizer import OptimizadorCarpooling


class Command(BaseCommand):
    help = 'Genera usuarios, vehículos y disponibilidades de prueba para verificar el optimizador'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando creación de datos de prueba..."))

        # 1. Superusuario administrador
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser('admin', 'admin@ejemplo.com', 'admin123')
            admin_user.first_name = "Administrador"
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Superusuario creado: admin / admin123"))

        # 2. Usuarios de prueba
        usuarios_data = [
            ('carlos', 'Carlos', 'Gómez', 'Peugeot 308', 5, True, 2, 4),
            ('ana', 'Ana', 'Martínez', 'Toyota Corolla', 5, True, 1, 5),
            ('david', 'David', 'López', 'Seat Ibiza', 4, True, 3, 3),
            ('elena', 'Elena', 'Ruiz', 'Ford Fiesta', 4, True, 1, 4),
            ('fernando', 'Fernando', 'Sanz', 'Volkswagen Polo', 4, True, 2, 3),
            ('lucia', 'Lucía', 'Navarro', None, 0, False, 0, 6),
            ('miguel', 'Miguel', 'Torres', 'Renault Megane', 5, False, 2, 4), # Coche en taller
            ('sara', 'Sara', 'Blanco', None, 0, False, 0, 5),
            ('pablo', 'Pablo', 'Vargas', 'Hyundai Tucson', 5, True, 0, 5),
        ]

        usuarios_creados = []
        for username, fname, lname, coche, plazas, coche_activo, cond, pas in usuarios_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': fname, 'last_name': lname, 'email': f"{username}@empresa.com"}
            )
            if created:
                user.set_password('demo1234')
                user.save()

            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            perfil.dias_conducidos = cond
            perfil.dias_pasajero = pas
            perfil.activo = True
            perfil.save()

            if coche:
                Vehiculo.objects.get_or_create(
                    propietario=user,
                    marca_modelo=coche,
                    defaults={'plazas_totales': plazas, 'activo': coche_activo}
                )

            usuarios_creados.append(user)

        self.stdout.write(self.style.SUCCESS(f"{len(usuarios_creados)} usuarios y vehículos configurados."))

        # 3. Generar disponibilidades para la semana próxima
        hoy = timezone.localdate()
        lunes = hoy - timedelta(days=hoy.weekday()) + timedelta(days=7)
        viernes = lunes + timedelta(days=4)

        for user in usuarios_creados:
            tiene_vehiculo = user.vehiculos.filter(activo=True).exists()
            for i in range(5):
                dia = lunes + timedelta(days=i)
                # Ejemplo de variaciones: Elena teletrabaja los miércoles, Fernando viernes libre
                asiste = True
                motivo = None
                if user.username == 'elena' and dia.weekday() == 2:
                    asiste = False
                    motivo = 'TELETRABAJO'
                elif user.username == 'fernando' and dia.weekday() == 4:
                    asiste = False
                    motivo = 'VACACIONES'

                DisponibilidadDiaria.objects.update_or_create(
                    usuario=user,
                    fecha=dia,
                    defaults={
                        'asiste': asiste,
                        'puede_conducir': tiene_vehiculo if asiste else False,
                        'motivo_ausencia': motivo
                    }
                )

        # 4. Crear y optimizar el plan de prueba
        plan, _ = PlanSemanal.objects.get_or_create(
            semana_inicio=lunes,
            defaults={'semana_fin': viernes, 'publicado': True}
        )
        optimizador = OptimizadorCarpooling(plan)
        resultado = optimizador.ejecutar_planificacion_semanal()

        self.stdout.write(self.style.SUCCESS(
            f"Plan semanal de prueba optimizado para la semana del {lunes.strftime('%d/%m/%Y')}."
        ))
        self.stdout.write(self.style.SUCCESS("¡Datos de prueba listos!"))
