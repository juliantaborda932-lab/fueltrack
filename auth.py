"""Usuarios: registro (RF-01), inicio de sesión y bloqueo (RF-02), protección de contraseñas (RNF-03)."""
import re
from datetime import datetime, timedelta

import bcrypt
from sqlalchemy import insert, select, update

from db import suscripciones, usuarios

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15
PATRON_CORREO = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")


def validar_correo(correo: str) -> bool:
    return bool(PATRON_CORREO.match(correo or ""))


def generar_hash(clave: str) -> str:
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()


def verificar_clave(clave: str, hash_guardado: str) -> bool:
    return bcrypt.checkpw(clave.encode(), hash_guardado.encode())


def registrar(motor, nombre, correo, clave, acepta_politica):
    """RF-01. Devuelve (ok, mensaje)."""
    correo = (correo or "").strip().lower()
    if not acepta_politica:
        return False, "Debe aceptar la política de tratamiento de datos (Ley 1581 de 2012)."
    if not nombre.strip():
        return False, "Escriba su nombre."
    if not validar_correo(correo):
        return False, "Formato de correo inválido (ejemplo@dominio.com)."
    if len(clave) < 8:
        return False, "La contraseña debe tener mínimo 8 caracteres."
    with motor.begin() as con:
        if con.execute(select(usuarios.c.id_usuario).where(usuarios.c.correo == correo)).first():
            return False, "Ese correo ya está registrado."
        res = con.execute(insert(usuarios).values(
            nombre=nombre.strip(), correo=correo, contrasena_hash=generar_hash(clave),
            acepta_politica=True, intentos_fallidos=0, fecha_registro=datetime.now()))
        con.execute(insert(suscripciones).values(
            id_usuario=res.inserted_primary_key[0], plan="Gratis", estado="Activa"))
    return True, "Cuenta creada. ¡Bienvenido a FuelTrack!"


def iniciar_sesion(motor, correo, clave, ahora=None):
    """RF-02. Devuelve (usuario | None, mensaje)."""
    ahora = ahora or datetime.now()
    correo = (correo or "").strip().lower()
    with motor.begin() as con:
        fila = con.execute(select(usuarios).where(usuarios.c.correo == correo)).mappings().first()
        if not fila:
            return None, "Correo o contraseña incorrectos."
        if fila["bloqueado_hasta"] and fila["bloqueado_hasta"] > ahora:
            minutos = int((fila["bloqueado_hasta"] - ahora).total_seconds() // 60) + 1
            return None, f"Cuenta bloqueada por intentos fallidos. Intente en {minutos} minutos."
        if verificar_clave(clave, fila["contrasena_hash"]):
            con.execute(update(usuarios).where(usuarios.c.id_usuario == fila["id_usuario"])
                        .values(intentos_fallidos=0, bloqueado_hasta=None))
            return {"id_usuario": fila["id_usuario"], "nombre": fila["nombre"], "correo": fila["correo"]}, "Bienvenido"
        intentos = fila["intentos_fallidos"] + 1
        valores = {"intentos_fallidos": intentos}
        mensaje = f"Correo o contraseña incorrectos. Intento {intentos} de {MAX_INTENTOS}."
        if intentos >= MAX_INTENTOS:
            valores = {"intentos_fallidos": 0, "bloqueado_hasta": ahora + timedelta(minutes=MINUTOS_BLOQUEO)}
            mensaje = f"Cuenta bloqueada {MINUTOS_BLOQUEO} minutos por {MAX_INTENTOS} intentos fallidos."
        con.execute(update(usuarios).where(usuarios.c.id_usuario == fila["id_usuario"]).values(**valores))
    return None, mensaje
