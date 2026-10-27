"""Registro de tanqueos (RF-04) con cálculo de rendimiento (RF-06) y alertas (RF-07, RF-08)."""
from datetime import date

import pandas as pd
from sqlalchemy import insert, select, update

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
        previos = con.execute(select(tanqueos.c.id_tanqueo, tanqueos.c.fecha, tanqueos.c.kilometraje,
                                     tanqueos.c.galones, tanqueos.c.rendimiento_km_gal)
                              .where(tanqueos.c.id_vehiculo == id_vehiculo)
                              .order_by(tanqueos.c.kilometraje)).all()
        km = int(kilometraje)
        miles = lambda n: f"{n:,}".replace(",", ".")
        if any(p.kilometraje == km for p in previos):
            r["mensaje"] = f"Kilometraje inválido: ya existe un tanqueo con {miles(km)} km."
            return r
        anterior = next((p for p in reversed(previos) if p.kilometraje < km), None)   # tanqueo justo antes
        siguiente = next((p for p in previos if p.kilometraje > km), None)            # tanqueo justo después
        f_ant = pd.to_datetime(anterior.fecha).date() if anterior else None
        f_sig = pd.to_datetime(siguiente.fecha).date() if siguiente else None
        if siguiente is not None and fecha > f_sig:
            # Es el tanqueo más reciente por fecha pero con menos km que otro: error de digitación
            r["mensaje"] = f"Kilometraje inválido: debe ser mayor a {miles(previos[-1].kilometraje)} km."
            return r
        if anterior is not None and fecha < f_ant:
            r["mensaje"] = (f"El kilometraje no concuerda con la fecha: el {f_ant:%d/%m/%Y} "
                            f"el vehículo ya tenía {miles(anterior.kilometraje)} km.")
            return r
        rend = calcular_rendimiento(anterior.kilometraje, km, galones) if anterior else None
        con.execute(insert(tanqueos).values(
            id_vehiculo=id_vehiculo, fecha=fecha, galones=galones, precio_galon=precio_galon,
            valor_total=valor_total, kilometraje=km, rendimiento_km_gal=rend, origen=origen))
        r.update(ok=True, rendimiento=rend, mensaje="Tanqueo guardado.")
        if siguiente is not None:
            # Tanqueo olvidado (fecha anterior): se recalcula el rendimiento del tanqueo siguiente y no se generan alertas
            con.execute(update(tanqueos).where(tanqueos.c.id_tanqueo == siguiente.id_tanqueo).values(
                rendimiento_km_gal=calcular_rendimiento(km, siguiente.kilometraje, siguiente.galones)))
            r["mensaje"] = "Tanqueo anterior guardado. Se recalculó el rendimiento del tanqueo siguiente."
            return r
        ultimo_km = anterior.kilometraje if anterior else None
        previos = [(p.kilometraje, p.rendimiento_km_gal) for p in previos]
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
