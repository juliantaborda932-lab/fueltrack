"""Alertas de consumo (RF-07) y recordatorio de mantenimiento por correo (RF-08)."""
import smtplib
from datetime import datetime
from email.message import EmailMessage

import pandas as pd
from sqlalchemy import insert, select

from db import alertas, vehiculos

UMBRAL = 0.15  # 15 %


def es_consumo_anormal(rendimiento: float, promedio: float, umbral: float = UMBRAL) -> bool:
    if not rendimiento or not promedio:
        return False
    return rendimiento <= promedio * (1 - umbral)


def diferencia_porcentaje(rendimiento: float, promedio: float) -> int:
    return round((promedio - rendimiento) / promedio * 100)


def requiere_mantenimiento(km_anterior: int, km_actual: int, intervalo: int = 5000) -> bool:
    return intervalo > 0 and km_actual // intervalo > km_anterior // intervalo


def guardar(con, id_vehiculo, tipo, mensaje):
    con.execute(insert(alertas).values(id_vehiculo=id_vehiculo, tipo=tipo, mensaje=mensaje[:200], fecha=datetime.now()))


def enviar_correo(destino, asunto, cuerpo):
    """Envía el recordatorio por SMTP con TLS si hay credenciales en los secretos.
    Devuelve True si se envió; False si no hay configuración (modo prototipo)."""
    try:
        import streamlit as st
        cfg = st.secrets["smtp"]
    except Exception:
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = cfg["usuario"], destino, asunto
    msg.set_content(cuerpo)
    with smtplib.SMTP(cfg["servidor"], int(cfg["puerto"])) as s:
        s.starttls()
        s.login(cfg["usuario"], cfg["clave"])
        s.send_message(msg)
    return True


def listar(motor, id_usuario) -> pd.DataFrame:
    q = (select(alertas.c.fecha, vehiculos.c.placa, alertas.c.tipo, alertas.c.mensaje)
         .join(vehiculos, vehiculos.c.id_vehiculo == alertas.c.id_vehiculo)
         .where(vehiculos.c.id_usuario == id_usuario).order_by(alertas.c.fecha.desc()))
    with motor.connect() as con:
        return pd.DataFrame(con.execute(q).mappings().all())
