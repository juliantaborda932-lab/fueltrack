"""Registro de tanqueos (RF-04) con cálculo de rendimiento (RF-06) y alertas (RF-07, RF-08)."""
from datetime import date

import pandas as pd
from sqlalchemy import insert, select

import alertas
from db import tanqueos, vehiculos
from rendimiento import calcular_rendimiento, promedio_ultimos


def historial(motor, id_vehiculo) -> pd.DataFrame:
    with motor.connect() as con:
        filas = con.execute(select(tanqueos).where(tanqueos.c.id_vehiculo == id_vehiculo)
                            .order_by(tanqueos.c.kilometraje)).mappings().all()
    return pd.DataFrame(filas)


def registrar(motor, id_vehiculo, fecha, galones, precio_galon, valor_total, kilometraje,
              origen="MANUAL", correo_conductor=None):
    """Devuelve dict con ok, mensaje, rendimiento y alertas generadas."""
    r = {"ok": False, "mensaje": "", "rendimiento": None, "alertas": []}
    # Si falta el total o el precio, se calcula con los otros dos datos
    if valor_total <= 0 and galones > 0 and precio_galon > 0:
        valor_total = round(galones * precio_galon)
    elif precio_galon <= 0 and galones > 0 and valor_total > 0:
        precio_galon = round(valor_total / galones, 2)
    if fecha > date.today():
        r["mensaje"] = "La fecha no puede ser futura."
        return r
    if not (0 < galones <= 100) or precio_galon <= 0 or valor_total <= 0:
        r["mensaje"] = "Revise galones (0 a 100), precio y valor."
        return r
    with motor.begin() as con:
        veh = con.execute(select(vehiculos).where(vehiculos.c.id_vehiculo == id_vehiculo)).mappings().first()
        previos = con.execute(select(tanqueos.c.kilometraje, tanqueos.c.rendimiento_km_gal)
                              .where(tanqueos.c.id_vehiculo == id_vehiculo)
                              .order_by(tanqueos.c.kilometraje)).all()
        ultimo_km = previos[-1][0] if previos else None
        if ultimo_km is not None and kilometraje <= ultimo_km:
            r["mensaje"] = f"Kilometraje inválido: debe ser mayor a {ultimo_km:,} km.".replace(",", ".")
            return r
        rend = calcular_rendimiento(ultimo_km, kilometraje, galones) if ultimo_km is not None else None
        con.execute(insert(tanqueos).values(
            id_vehiculo=id_vehiculo, fecha=fecha, galones=galones, precio_galon=precio_galon,
            valor_total=valor_total, kilometraje=int(kilometraje), rendimiento_km_gal=rend, origen=origen))
        r.update(ok=True, rendimiento=rend, mensaje="Tanqueo guardado.")
        # RF-07: consumo anormal frente al promedio de los últimos 5
        prom = promedio_ultimos([p[1] for p in previos], 5)
        if rend and alertas.es_consumo_anormal(rend, prom):
            dif = alertas.diferencia_porcentaje(rend, prom)
            msg = f"Consumo {dif} % mayor de lo normal: {rend} km/gal frente a un promedio de {prom} km/gal."
            alertas.guardar(con, id_vehiculo, "CONSUMO", msg)
            r["alertas"].append(msg)
        # RF-08: recordatorio de mantenimiento
        if ultimo_km is not None and alertas.requiere_mantenimiento(ultimo_km, kilometraje, veh["km_mantenimiento"]):
            msg = f"Mantenimiento pendiente: el vehículo {veh['placa']} llegó a {int(kilometraje):,} km.".replace(",", ".")
            alertas.guardar(con, id_vehiculo, "MANTENIMIENTO", msg)
            enviado = correo_conductor and alertas.enviar_correo(correo_conductor, "Mantenimiento pendiente", msg)
            r["alertas"].append(msg + (" Se envió un correo." if enviado else " (Correo no configurado en el prototipo.)"))
    return r
