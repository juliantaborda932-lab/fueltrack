"""Plan premium (RF-11). En el prototipo se usa el modo de pruebas (sandbox) de la pasarela:
no se guardan datos de tarjeta (RD-02); solo la referencia y el estado del pago."""
import uuid
from datetime import datetime

from sqlalchemy import insert, select, update

from db import pagos, suscripciones

VALOR_PREMIUM = 9900  # COP mensual (valor de prueba)


def obtener_suscripcion(motor, id_usuario):
    with motor.connect() as con:
        return con.execute(select(suscripciones).where(suscripciones.c.id_usuario == id_usuario)).mappings().first()


def iniciar_pago(motor, id_usuario):
    """Crea la referencia del pago y devuelve los datos para la pasarela."""
    referencia = "FT-" + uuid.uuid4().hex[:10].upper()
    sus = obtener_suscripcion(motor, id_usuario)
    with motor.begin() as con:
        con.execute(insert(pagos).values(id_suscripcion=sus["id_suscripcion"], referencia_pasarela=referencia,
                                         valor=VALOR_PREMIUM, estado="PENDIENTE", fecha=datetime.now()))
    return {"referencia": referencia, "valor": VALOR_PREMIUM}


def confirmar_pago(motor, referencia, aprobado: bool):
    """Lo llama la confirmación de la pasarela. Si es aprobado, activa el plan premium."""
    with motor.begin() as con:
        pago = con.execute(select(pagos).where(pagos.c.referencia_pasarela == referencia)).mappings().first()
        if not pago:
            return False
        con.execute(update(pagos).where(pagos.c.id_pago == pago["id_pago"])
                    .values(estado="APROBADO" if aprobado else "RECHAZADO"))
        if aprobado:
            con.execute(update(suscripciones).where(suscripciones.c.id_suscripcion == pago["id_suscripcion"])
                        .values(plan="Premium", estado="Activa"))
    return aprobado
