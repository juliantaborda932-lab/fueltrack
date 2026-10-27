"""Conexión a la base de datos y definición de tablas (modelo físico).

En producción se usa PostgreSQL de Supabase (API-01) leyendo DATABASE_URL de los secretos.
Si no hay secretos, se usa un archivo SQLite local para pruebas.
"""
import os

from sqlalchemy import (Boolean, Column, Date, DateTime, Float, ForeignKey, Integer,
                        MetaData, String, Table, Text, create_engine)

metadata = MetaData()

usuarios = Table(
    "usuarios", metadata,
    Column("id_usuario", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String(80), nullable=False),
    Column("correo", String(120), nullable=False, unique=True),
    Column("contrasena_hash", String(60), nullable=False),
    Column("acepta_politica", Boolean, nullable=False),
    Column("intentos_fallidos", Integer, nullable=False, default=0),
    Column("bloqueado_hasta", DateTime, nullable=True),
    Column("fecha_registro", DateTime, nullable=False),
)

vehiculos = Table(
    "vehiculos", metadata,
    Column("id_vehiculo", Integer, primary_key=True, autoincrement=True),
    Column("id_usuario", Integer, ForeignKey("usuarios.id_usuario"), nullable=False),
    Column("placa", String(6), nullable=False, unique=True),
    Column("marca", String(40), nullable=False),
    Column("modelo", String(40), nullable=False),
    Column("anio", Integer, nullable=False),
    Column("tipo_combustible", String(15), nullable=False),
    Column("km_mantenimiento", Integer, nullable=False, default=5000),
)

estaciones = Table(
    "estaciones", metadata,
    Column("id_estacion", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String(100), nullable=False),
    Column("latitud", Float, nullable=False),
    Column("longitud", Float, nullable=False),
    Column("aliada", Boolean, nullable=False, default=False),
)

precios = Table(
    "precios", metadata,
    Column("id_precio", Integer, primary_key=True, autoincrement=True),
    Column("id_estacion", Integer, ForeignKey("estaciones.id_estacion"), nullable=False),
    Column("tipo_combustible", String(15), nullable=False),
    Column("precio_galon", Float, nullable=False),
    Column("fecha_actualizacion", DateTime, nullable=False),
)

tanqueos = Table(
    "tanqueos", metadata,
    Column("id_tanqueo", Integer, primary_key=True, autoincrement=True),
    Column("id_vehiculo", Integer, ForeignKey("vehiculos.id_vehiculo"), nullable=False),
    Column("id_estacion", Integer, ForeignKey("estaciones.id_estacion"), nullable=True),
    Column("fecha", Date, nullable=False),
    Column("galones", Float, nullable=False),
    Column("precio_galon", Float, nullable=False),
    Column("valor_total", Float, nullable=False),
    Column("kilometraje", Integer, nullable=False),
    Column("rendimiento_km_gal", Float, nullable=True),
    Column("origen", String(6), nullable=False),
)

alertas = Table(
    "alertas", metadata,
    Column("id_alerta", Integer, primary_key=True, autoincrement=True),
    Column("id_vehiculo", Integer, ForeignKey("vehiculos.id_vehiculo"), nullable=False),
    Column("tipo", String(15), nullable=False),
    Column("mensaje", String(200), nullable=False),
    Column("fecha", DateTime, nullable=False),
)

suscripciones = Table(
    "suscripciones", metadata,
    Column("id_suscripcion", Integer, primary_key=True, autoincrement=True),
    Column("id_usuario", Integer, ForeignKey("usuarios.id_usuario"), nullable=False, unique=True),
    Column("plan", String(10), nullable=False),
    Column("estado", String(10), nullable=False),
)

pagos = Table(
    "pagos", metadata,
    Column("id_pago", Integer, primary_key=True, autoincrement=True),
    Column("id_suscripcion", Integer, ForeignKey("suscripciones.id_suscripcion"), nullable=False),
    Column("referencia_pasarela", String(50), nullable=False, unique=True),
    Column("valor", Float, nullable=False),
    Column("estado", String(10), nullable=False),
    Column("fecha", DateTime, nullable=False),
)

solicitudes_soporte = Table(
    "solicitudes_soporte", metadata,
    Column("radicado", String(12), primary_key=True),
    Column("id_usuario", Integer, ForeignKey("usuarios.id_usuario"), nullable=False),
    Column("categoria", String(30), nullable=False),
    Column("descripcion", Text, nullable=False),
    Column("estado", String(10), nullable=False),
    Column("fecha", DateTime, nullable=False),
)


def url_bd():
    """Busca DATABASE_URL en los secretos de Streamlit o en variables de entorno."""
    try:
        import streamlit as st
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    return os.environ.get("DATABASE_URL", "sqlite:///fueltrack.db")


def crear_motor(url=None):
    motor = create_engine(url or url_bd(), pool_pre_ping=True)
    metadata.create_all(motor)
    return motor
