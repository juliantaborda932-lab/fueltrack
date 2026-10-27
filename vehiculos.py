"""Vehículos (RF-03)."""
import re
from datetime import date

import pandas as pd
from sqlalchemy import insert, select

from db import vehiculos

COMBUSTIBLES = ["Corriente", "Extra", "Diésel"]
PATRON_PLACA = re.compile(r"^[A-Z]{3}[0-9]{3}$")


def validar_placa(placa: str) -> bool:
    return bool(PATRON_PLACA.match((placa or "").strip().upper()))


def registrar(motor, id_usuario, placa, marca, modelo, anio, combustible, km_mantenimiento=5000):
    placa = (placa or "").strip().upper()
    if not validar_placa(placa):
        return False, "Formato de placa AAA123 (3 letras y 3 números)."
    if not marca.strip() or not modelo.strip():
        return False, "Escriba la marca y el modelo."
    if not 1980 <= int(anio) <= date.today().year + 1:
        return False, "Año fuera de rango."
    if combustible not in COMBUSTIBLES:
        return False, "Tipo de combustible inválido."
    with motor.begin() as con:
        if con.execute(select(vehiculos.c.id_vehiculo).where(vehiculos.c.placa == placa)).first():
            return False, "Esa placa ya está registrada."
        con.execute(insert(vehiculos).values(
            id_usuario=id_usuario, placa=placa, marca=marca.strip(), modelo=modelo.strip(),
            anio=int(anio), tipo_combustible=combustible, km_mantenimiento=int(km_mantenimiento)))
    return True, f"Vehículo {placa} registrado."


def listar(motor, id_usuario) -> pd.DataFrame:
    with motor.connect() as con:
        filas = con.execute(select(vehiculos).where(vehiculos.c.id_usuario == id_usuario)
                            .order_by(vehiculos.c.id_vehiculo)).mappings().all()
    return pd.DataFrame(filas)
