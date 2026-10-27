"""Cálculo de rendimiento (RF-06)."""
from typing import List, Optional


def calcular_rendimiento(km_anterior: int, km_actual: int, galones: float) -> Optional[float]:
    """km/galón = km recorridos ÷ galones cargados."""
    if galones is None or galones <= 0 or km_actual <= km_anterior:
        return None
    return round((km_actual - km_anterior) / galones, 2)


def promedio_ultimos(valores: List[float], n: int = 5) -> Optional[float]:
    validos = [v for v in valores if v]
    ultimos = validos[-n:]
    return round(sum(ultimos) / len(ultimos), 2) if ultimos else None
