from django.test import TestCase
from django.contrib.auth.models import User
from datetime import date
from carpooling.models import Vehiculo, PerfilUsuario, PlanSemanal
from carpooling.services.optimizer import OptimizadorCarpooling


class OptimizadorCarpoolingTestCase(TestCase):
    def setUp(self):
        # Crear 9 usuarios
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
        # Debe usar exactamente 2 coches
        self.assertEqual(len(mejor_comb), 2)
        # La capacidad total debe ser al menos 9
        capacidad = sum(c['plazas'] for c in mejor_comb)
        self.assertGreaterEqual(capacidad, 9)
        # Debe haber elegido los dos de 5 plazas (5+5=10)
        plazas = sorted([c['plazas'] for c in mejor_comb])
        self.assertEqual(plazas, [5, 5])
