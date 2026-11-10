from django.test import TestCase
from django.contrib.auth.models import User
from datetime import date
from carpooling.models import Vehiculo, PerfilUsuario, PlanSemanal, AsignacionDia, DisponibilidadDiaria
from carpooling.services.optimizer import OptimizadorCarpooling


class OptimizadorCarpoolingTestCase(TestCase):
    def setUp(self):
        # Crear 9 usuarios activos
        self.usuarios = []
        for i in range(1, 10):
            u = User.objects.create_user(username=f'user{i}', password='password')
            u.perfil.activo = True
            u.perfil.save()
            self.usuarios.append(u)

        # Coches de 5 plazas (user1, user2)
        Vehiculo.objects.create(propietario=self.usuarios[0], marca_modelo="Coche 5 plazas A", plazas_totales=5, activo=True)
        Vehiculo.objects.create(propietario=self.usuarios[1], marca_modelo="Coche 5 plazas B", plazas_totales=5, activo=True)

        # Coches de 4 plazas (user3, user4, user5)
        Vehiculo.objects.create(propietario=self.usuarios[2], marca_modelo="Coche 4 plazas C", plazas_totales=4, activo=True)
        Vehiculo.objects.create(propietario=self.usuarios[3], marca_modelo="Coche 4 plazas D", plazas_totales=4, activo=True)
        Vehiculo.objects.create(propietario=self.usuarios[4], marca_modelo="Coche 4 plazas E", plazas_totales=4, activo=True)

        self.plan = PlanSemanal.objects.create(
            semana_inicio=date(2026, 11, 2),
            semana_fin=date(2026, 11, 6)
        )
        self.optimizador = OptimizadorCarpooling(self.plan)

    def test_minimizacion_de_coches_para_9_personas(self):
        """
        Para 9 personas viajando, con coches de 5, 5, 4, 4 y 4 plazas:
        El optimizador debe elegir 2 coches (5+5=10 plazas) en lugar de 3 coches (4+4+4=12).
        """
        candidatos = [
            {'usuario': self.usuarios[0], 'plazas': 5, 'score': 0.0},
            {'usuario': self.usuarios[1], 'plazas': 5, 'score': 0.0},
            {'usuario': self.usuarios[2], 'plazas': 4, 'score': 0.0},
            {'usuario': self.usuarios[3], 'plazas': 4, 'score': 0.0},
            {'usuario': self.usuarios[4], 'plazas': 4, 'score': 0.0},
        ]

        mejor_comb = self.optimizador._encontrar_mejor_combinacion_coches(
            candidatos=candidatos,
            pasajeros_necesarios=9
        )

        self.assertIsNotNone(mejor_comb)
        self.assertEqual(len(mejor_comb), 2)
        capacidad = sum(c['plazas'] for c in mejor_comb)
        self.assertGreaterEqual(capacidad, 9)
        plazas = sorted([c['plazas'] for c in mejor_comb])
        self.assertEqual(plazas, [5, 5])

    def test_optimizacion_sin_disponibilidad_previa(self):
        """
        Verifica que se pueden generar turnos para cualquier semana
        SIN necesidad de que ningún usuario haya entrado a 'Mi Disponibilidad'.
        Por defecto, todos los usuarios activos viajan y aportan coche.
        """
        # No hay ningún registro en DisponibilidadDiaria
        self.assertEqual(DisponibilidadDiaria.objects.count(), 0)

        # Generar plan
        res = self.optimizador.ejecutar_planificacion_semanal()
        self.assertEqual(res['dias_optimizados'], 5)

        for dia in self.plan.dias.all():
            self.assertEqual(dia.total_viajeros, 9)
            self.assertEqual(dia.total_coches, 2)
            self.assertEqual(dia.viajes_vehiculo.count(), 2)

    def test_notificacion_ausencia_y_recalculo(self):
        """
        Si un usuario notifica ausencia (ej. vacaciones), el optimizador
        lo excluye de los viajeros y ajusta los vehículos.
        """
        lunes = date(2026, 11, 2)

        # User1 notifica que no asiste el lunes por vacaciones
        DisponibilidadDiaria.objects.create(
            usuario=self.usuarios[0],
            fecha=lunes,
            asiste=False,
            motivo_ausencia='VACACIONES'
        )

        res = self.optimizador.ejecutar_planificacion_semanal()
        self.assertEqual(res['dias_optimizados'], 5)

        asignacion_lunes = self.plan.dias.get(fecha=lunes)
        # Solo viajan 8 personas el lunes
        self.assertEqual(asignacion_lunes.total_viajeros, 8)
        # User1 no debe ser conductor el lunes
        conductores_lunes = [v.conductor for v in asignacion_lunes.viajes_vehiculo.all()]
        self.assertNotIn(self.usuarios[0], conductores_lunes)

        # En los demás días viajan 9 personas
        asignacion_martes = self.plan.dias.get(fecha=date(2026, 11, 3))
        self.assertEqual(asignacion_martes.total_viajeros, 9)
