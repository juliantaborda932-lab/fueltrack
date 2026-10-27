"""Solicitudes de soporte (RF-12)."""
from datetime import datetime

from sqlalchemy import func, insert, select

from db import solicitudes_soporte

CATEGORIAS = ["Registro de tanqueo", "Lectura del ticket (OCR)", "Precios", "Reportes", "Pagos", "Otro"]


def generar_radicado(anio: int, consecutivo: int) -> str:
    return f"SOP-{anio}-{consecutivo:04d}"


def registrar(motor, id_usuario, categoria, descripcion):
    if len((descripcion or "").strip()) < 10:
        return False, "La descripción debe tener mínimo 10 caracteres."
    anio = datetime.now().year
    with motor.begin() as con:
        n = con.execute(select(func.count()).select_from(solicitudes_soporte)
                        .where(solicitudes_soporte.c.radicado.like(f"SOP-{anio}-%"))).scalar()
        radicado = generar_radicado(anio, n + 1)
        con.execute(insert(solicitudes_soporte).values(
            radicado=radicado, id_usuario=id_usuario, categoria=categoria,
            descripcion=descripcion.strip(), estado="Abierta", fecha=datetime.now()))
    return True, radicado
