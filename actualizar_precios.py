"""Actualización diaria de precios (RNF-07). Lo ejecuta GitHub Actions todos los días antes de las 6:00 a. m.
Fuente: archivo de estaciones aliadas (data/precios_aliadas.csv). Los valores de este archivo son DATOS DE PRUEBA."""
import csv
import os
from datetime import datetime

from sqlalchemy import insert, select

from db import crear_motor, estaciones, precios

ARCHIVO = os.path.join(os.path.dirname(__file__), "data", "precios_aliadas.csv")


def cargar(motor, archivo=ARCHIVO, ahora=None):
    ahora = ahora or datetime.now()
    n = 0
    with open(archivo, encoding="utf-8") as f, motor.begin() as con:
        for fila in csv.DictReader(f):
            est = con.execute(select(estaciones.c.id_estacion).where(estaciones.c.nombre == fila["estacion"])).first()
            if est:
                id_est = est[0]
            else:
                id_est = con.execute(insert(estaciones).values(
                    nombre=fila["estacion"], latitud=float(fila["latitud"]), longitud=float(fila["longitud"]),
                    aliada=fila["aliada"] == "1")).inserted_primary_key[0]
            con.execute(insert(precios).values(id_estacion=id_est, tipo_combustible=fila["tipo_combustible"],
                                               precio_galon=float(fila["precio_galon"]), fecha_actualizacion=ahora))
            n += 1
    return n


if __name__ == "__main__":
    print(f"Precios actualizados: {cargar(crear_motor())}")
