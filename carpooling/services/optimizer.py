"""
Motor de optimización para el reparto equilibrado y minimización de vehículos.
"""
import itertools
from datetime import timedelta
from typing import List, Dict, Any, Tuple
from django.contrib.auth.models import User
from carpooling.models import (
    Vehiculo, DisponibilidadDiaria, PlanSemanal, AsignacionDia, ViajeVehiculo, PerfilUsuario
)


class OptimizadorCarpooling:
    def __init__(self, plan: PlanSemanal):
        self.plan = plan

    def ejecutar_planificacion_semanal(self) -> Dict[str, Any]:
        """
        Ejecuta la optimización para cada uno de los días del plan semanal (Lunes a Viernes).
        """
        fecha_actual = self.plan.semana_inicio
        fin = self.plan.semana_fin

        # Contador de veces que ha conducido cada usuario DENTRO de esta misma semana
        conducciones_semana = {u.id: 0 for u in User.objects.filter(perfil__activo=True)}

        resultados_dias = []

        while fecha_actual <= fin:
            res_dia = self._optimizar_dia(fecha_actual, conducciones_semana)
            resultados_dias.append(res_dia)
            
            # Sumar al contador semanal para rotar conductores
            for conductor_id in res_dia.get('conductores_asignados', []):
                conducciones_semana[conductor_id] = conducciones_semana.get(conductor_id, 0) + 1

            # Avanzar al siguiente día
            fecha_actual += timedelta(days=1)

        return {
            'plan_id': self.plan.id,
            'dias_optimizados': len(resultados_dias),
            'detalles': resultados_dias
        }

    def _optimizar_dia(self, fecha, conducciones_semana: Dict[int, int]) -> Dict[str, Any]:
        """
        Calcula la selección óptima de vehículos y pasajeros para un día específico.
        """
        # 1. Obtener disponibilidades para este día
        disponibilidades = DisponibilidadDiaria.objects.filter(
            fecha=fecha,
            usuario__perfil__activo=True
        ).select_related('usuario', 'usuario__perfil')

        viajeros = []
        candidatos_conductores = []

        for disp in disponibilidades:
            if disp.asiste:
                viajeros.append(disp.usuario)
                
                # Verificar si puede aportar coche
                if disp.puede_conducir:
                    vehiculo = disp.usuario.vehiculos.filter(activo=True).first()
                    if vehiculo and vehiculo.plazas_totales > 1:
                        # Calcular score de prioridad de conducción
                        # Cuanto MENOR sea el score, más prioridad tiene de poner el coche hoy.
                        perfil = getattr(disp.usuario, 'perfil', None)
                        ratio_historico = perfil.ratio_aportacion if perfil else 0.0
                        conducidos_esta_semana = conducciones_semana.get(disp.usuario.id, 0)
                        
                        # Penalización alta por haber conducido ya esta misma semana (favorece rotación semanal)
                        score = (ratio_historico * 10.0) + (conducidos_esta_semana * 50.0)

                        candidatos_conductores.append({
                            'usuario': disp.usuario,
                            'vehiculo': vehiculo,
                            'plazas': vehiculo.plazas_totales,
                            'score': score
                        })

        total_viajeros = len(viajeros)

        # Crear o limpiar registro AsignacionDia
        asignacion_dia, _ = AsignacionDia.objects.update_or_create(
            plan=self.plan,
            fecha=fecha,
            defaults={
                'total_viajeros': total_viajeros,
                'total_coches': 0
            }
        )
        # Limpiar viajes previos si se está regenerando
        asignacion_dia.viajes_vehiculo.all().delete()

        # Si nadie viaja o solo viaja 1 persona sin coche
        if total_viajeros == 0:
            return {
                'fecha': fecha,
                'total_viajeros': 0,
                'total_coches': 0,
                'conductores_asignados': []
            }

        # 2. Algoritmo de selección de vehículos óptimos
        mejor_combinacion = self._encontrar_mejor_combinacion_coches(
            candidatos=candidatos_conductores,
            pasajeros_necesarios=total_viajeros
        )

        conductores_ids = []
        if mejor_combinacion:
            conductores = [c['usuario'] for c in mejor_combinacion]
            conductores_ids = [u.id for u in conductores]
            
            # Pasajeros que no conducen hoy
            pasajeros_restantes = [u for u in viajeros if u not in conductores]

            # Crear registros de ViajeVehiculo y asignar pasajeros a los coches
            for cand in mejor_combinacion:
                viaje = ViajeVehiculo.objects.create(
                    asignacion_dia=asignacion_dia,
                    conductor=cand['usuario'],
                    vehiculo=cand['vehiculo']
                )
                
                # Asignar pasajeros hasta llenar las plazas útiles del coche (plazas_totales - 1)
                capacidad_pasajeros = cand['vehiculo'].plazas_pasajeros
                pasajeros_este_coche = pasajeros_restantes[:capacidad_pasajeros]
                pasajeros_restantes = pasajeros_restantes[capacidad_pasajeros:]
                
                if pasajeros_este_coche:
                    viaje.pasajeros.set(pasajeros_este_coche)

            asignacion_dia.total_coches = len(mejor_combinacion)
            asignacion_dia.save()

        return {
            'fecha': fecha,
            'total_viajeros': total_viajeros,
            'total_coches': len(mejor_combinacion) if mejor_combinacion else 0,
            'conductores_asignados': conductores_ids,
            'sin_plazas_suficientes': (mejor_combinacion is None)
        }

    def _encontrar_mejor_combinacion_coches(
        self, candidatos: List[Dict[str, Any]], pasajeros_necesarios: int
    ) -> List[Dict[str, Any]]:
        """
        Encuentra el conjunto de vehículos que:
        1. Minimiza el número total de coches necesarios (sum(plazas) >= pasajeros_necesarios).
        2. Minimiza el exceso de plazas sobrantes (ej. 5+5 es mejor que 5+7 si se necesitan 9).
        3. Minimiza la suma de scores de equidad (prioriza a quienes han conducido menos).
        """
        if not candidatos:
            return None

        capacidad_max_posible = sum(c['plazas'] for c in candidatos)
        if capacidad_max_posible < pasajeros_necesarios:
            # No hay suficientes plazas ni usando todos los coches disponibles
            return None

        # Evaluamos combinaciones de tamaño 1, 2, 3... hasta len(candidatos)
        # El primer tamaño k que logre cubrir a los pasajeros garantiza el MÍNIMO número de coches.
        for tamano_k in range(1, len(candidatos) + 1):
            combinaciones_validas = []

            for comb in itertools.combinations(candidatos, tamano_k):
                capacidad_total = sum(c['plazas'] for c in comb)
                if capacidad_total >= pasajeros_necesarios:
                    exceso_plazas = capacidad_total - pasajeros_necesarios
                    score_equidad = sum(c['score'] for c in comb)
                    
                    # Criterio de orden:
                    # 1. Menor exceso de plazas (más ajustado a la capacidad requerida)
                    # 2. Menor score de equidad (conduce quien más lo debe)
                    combinaciones_validas.append((exceso_plazas, score_equidad, comb))

            if combinaciones_validas:
                # Ordenar por (menor exceso, menor score)
                combinaciones_validas.sort(key=lambda x: (x[0], x[1]))
                mejor = combinaciones_validas[0][2]
                return list(mejor)

        return None
