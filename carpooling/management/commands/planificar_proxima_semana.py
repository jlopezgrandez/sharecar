"""
Comando para ejecución desatendida/automática (Cron Job).
Calcula y publica automáticamente el plan de la semana siguiente.
Uso: python manage.py planificar_proxima_semana
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from carpooling.models import PlanSemanal
from carpooling.services.optimizer import OptimizadorCarpooling


class Command(BaseCommand):
    help = 'Genera y optimiza de forma automática el plan de coche compartido para la próxima semana'

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        # Próximo lunes (semana entrante)
        lunes_proximo = hoy - timedelta(days=hoy.weekday()) + timedelta(days=7)
        viernes_proximo = lunes_proximo + timedelta(days=4)

        self.stdout.write(f"Iniciando planificación automática para la semana del {lunes_proximo.strftime('%d/%m/%Y')}...")

        plan, _ = PlanSemanal.objects.get_or_create(
            semana_inicio=lunes_proximo,
            defaults={
                'semana_fin': viernes_proximo,
                'publicado': True,
                'notas': 'Generado automáticamente por el sistema.'
            }
        )
        plan.semana_fin = viernes_proximo
        plan.publicado = True
        plan.save()

        optimizador = OptimizadorCarpooling(plan)
        resultado = optimizador.ejecutar_planificacion_semanal()

        self.stdout.write(self.style.SUCCESS(
            f"¡Plan generado con éxito! Se optimizaron {resultado['dias_optimizados']} días."
        ))
