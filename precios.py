"""Comparación de precios cercanos (RF-09)."""
import pandas as pd
from sqlalchemy import func, select

from db import estaciones, precios
from modelos import Estacion, Ubicacion

RADIO_KM = 5.0


def ultimos_precios(motor, tipo_combustible) -> pd.DataFrame:
    sub = (select(precios.c.id_estacion, func.max(precios.c.fecha_actualizacion).label("f"))
           .where(precios.c.tipo_combustible == tipo_combustible).group_by(precios.c.id_estacion).subquery())
    q = (select(estaciones.c.id_estacion, estaciones.c.nombre, estaciones.c.latitud, estaciones.c.longitud,
                estaciones.c.aliada, precios.c.precio_galon, precios.c.fecha_actualizacion)
         .join(precios, precios.c.id_estacion == estaciones.c.id_estacion)
         .join(sub, (sub.c.id_estacion == precios.c.id_estacion) & (sub.c.f == precios.c.fecha_actualizacion))
         .where(precios.c.tipo_combustible == tipo_combustible))
    with motor.connect() as con:
        return pd.DataFrame(con.execute(q).mappings().all())


def estaciones_cercanas(df: pd.DataFrame, lat: float, lon: float, radio_km: float = RADIO_KM) -> pd.DataFrame:
    if df.empty:
        return df
    desde = Ubicacion(lat, lon)
    df = df.copy()
    df["distancia_km"] = [round(Estacion(0, "", Ubicacion(a, b)).distancia_km(desde), 1)
                          for a, b in zip(df["latitud"], df["longitud"])]
    return df[df["distancia_km"] <= radio_km].sort_values(["precio_galon", "distancia_km"]).reset_index(drop=True)
