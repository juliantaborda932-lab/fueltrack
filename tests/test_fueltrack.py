"""Pruebas automáticas (RNF-08). Cada prueba indica el caso de prueba (CP) que automatiza."""
import os
import sys
from datetime import date, datetime, timedelta

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import alertas  # noqa: E402
import auth  # noqa: E402
import ocr  # noqa: E402
import pagos  # noqa: E402
import precios  # noqa: E402
import reportes  # noqa: E402
import soporte  # noqa: E402
import tanqueos  # noqa: E402
import vehiculos  # noqa: E402
from actualizar_precios import cargar  # noqa: E402
from db import crear_motor  # noqa: E402
from rendimiento import calcular_rendimiento, promedio_ultimos  # noqa: E402


@pytest.fixture
def motor():
    return crear_motor("sqlite://")


@pytest.fixture
def con_vehiculo(motor):
    auth.registrar(motor, "Ana Gómez", "ana@mail.com", "Fuel2026*", True)
    usuario, _ = auth.iniciar_sesion(motor, "ana@mail.com", "Fuel2026*")
    vehiculos.registrar(motor, usuario["id_usuario"], "ABC123", "Chevrolet", "Spark GT", 2018, "Corriente")
    veh = vehiculos.listar(motor, usuario["id_usuario"]).iloc[0]
    return motor, usuario, int(veh["id_vehiculo"])


# CP-RF01-01 / CP-RF01-02
def test_registro_cuenta(motor):
    assert auth.registrar(motor, "Ana", "ana@mail.com", "Fuel2026*", True)[0]
    assert not auth.registrar(motor, "Ana", "ana@mail.com", "Fuel2026*", True)[0]      # correo repetido
    ok, msg = auth.registrar(motor, "Luis", "luis@mail.com", "Fuel2026*", False)
    assert not ok and "política" in msg


# CP-RF02-01 / CP-RF02-02
def test_inicio_sesion_y_bloqueo(motor):
    auth.registrar(motor, "Ana", "ana@mail.com", "Fuel2026*", True)
    assert auth.iniciar_sesion(motor, "ana@mail.com", "Fuel2026*")[0] is not None
    t0 = datetime(2026, 10, 20, 8, 0)
    for _ in range(5):
        usuario, msg = auth.iniciar_sesion(motor, "ana@mail.com", "mala", ahora=t0)
    assert usuario is None and "bloqueada" in msg
    assert auth.iniciar_sesion(motor, "ana@mail.com", "Fuel2026*", ahora=t0 + timedelta(minutes=5))[0] is None
    assert auth.iniciar_sesion(motor, "ana@mail.com", "Fuel2026*", ahora=t0 + timedelta(minutes=16))[0] is not None


# CP-RNF03-02
def test_contrasena_con_hash():
    h = auth.generar_hash("Fuel2026*")
    assert h != "Fuel2026*" and h.startswith("$2") and auth.verificar_clave("Fuel2026*", h)


# CP-RF03-01
def test_placa():
    assert vehiculos.validar_placa("ABC123") and not vehiculos.validar_placa("AB12")


# CP-RF04-01 / CP-RF04-02 / CP-RF06-01
def test_tanqueos_y_rendimiento(con_vehiculo):
    motor, _, idv = con_vehiculo
    assert tanqueos.registrar(motor, idv, date(2026, 10, 1), 10, 16000, 160000, 45200)["ok"]
    r = tanqueos.registrar(motor, idv, date(2026, 10, 8), 10, 16000, 160000, 45560)
    assert r["ok"] and r["rendimiento"] == 36.0
    r = tanqueos.registrar(motor, idv, date(2026, 10, 9), 10, 16000, 160000, 45000)
    assert not r["ok"] and "Kilometraje inválido" in r["mensaje"]


# CP-RF07-01
def test_alerta_consumo(con_vehiculo):
    motor, usuario, idv = con_vehiculo
    km = 40000
    tanqueos.registrar(motor, idv, date(2026, 9, 1), 10, 16000, 160000, km)
    for d in range(2, 7):                       # 5 tanqueos a 40 km/gal
        km += 400
        tanqueos.registrar(motor, idv, date(2026, 9, d), 10, 16000, 160000, km)
    r = tanqueos.registrar(motor, idv, date(2026, 9, 10), 10, 16000, 160000, km + 320)   # 32 km/gal
    assert any("20 %" in a for a in r["alertas"])
    assert not alertas.listar(motor, usuario["id_usuario"]).empty


# CP-RF08-01
def test_recordatorio_mantenimiento(con_vehiculo):
    motor, _, idv = con_vehiculo
    tanqueos.registrar(motor, idv, date(2026, 9, 1), 10, 16000, 160000, 49800)
    r = tanqueos.registrar(motor, idv, date(2026, 9, 5), 10, 16000, 160000, 50100)
    assert any("Mantenimiento pendiente" in a for a in r["alertas"])
    assert alertas.requiere_mantenimiento(4900, 5100) and not alertas.requiere_mantenimiento(5100, 5200)


def test_funciones_calculo():
    assert calcular_rendimiento(45200, 45560, 10) == 36.0
    assert calcular_rendimiento(45200, 45000, 10) is None and calcular_rendimiento(1, 2, 0) is None
    assert promedio_ultimos([30, 40, 40, 40, 40, 40]) == 40.0 and promedio_ultimos([]) is None
    assert alertas.es_consumo_anormal(32, 40) and not alertas.es_consumo_anormal(36, 40)
    assert not alertas.es_consumo_anormal(None, 40)
    assert alertas.diferencia_porcentaje(32, 40) == 20


# CP-RF05-01 (parte de interpretación del texto leído por OCR)
def test_extraer_datos_ticket():
    texto = "ESTACION LAURELES\nGalones: 10,250\nPrecio/gal: $16.150\nTOTAL: $165.538\n"
    d = ocr.extraer_datos(texto)
    assert d.galones == 10.25 and d.precio_galon == 16150 and d.valor_total == 165538


# CP-RF09-01
def test_precios_cercanos(motor):
    cargar(motor)
    df = precios.estaciones_cercanas(precios.ultimos_precios(motor, "Corriente"), 6.2442, -75.5812)
    assert not df.empty and (df["distancia_km"] <= 5).all()
    assert list(df["precio_galon"]) == sorted(df["precio_galon"])


# CP-RF10-01 / CP-RF10-02
def test_reporte_mensual(con_vehiculo):
    motor, _, idv = con_vehiculo
    for d, km in [(5, 45000), (15, 45360), (25, 45720)]:
        tanqueos.registrar(motor, idv, date(2026, 9, d), 10, 16000, 160000, km)
    rep = reportes.resumen_mes(tanqueos.historial(motor, idv), "2026-09")
    assert rep.gasto_total == 480000 and rep.rendimiento_promedio == 36.0
    assert not reportes.gasto_por_semana(rep).empty
    assert reportes.exportar_pdf(rep, "ABC123", "Ana")[:4] == b"%PDF"
    assert reportes.resumen_mes(pd.DataFrame(), "2026-09").gasto_total == 0


# CP-RF11-01 / CP-RF11-02
def test_plan_premium(con_vehiculo):
    motor, usuario, _ = con_vehiculo
    p = pagos.iniciar_pago(motor, usuario["id_usuario"])
    assert p["referencia"].startswith("FT-")
    assert pagos.confirmar_pago(motor, p["referencia"], True)
    assert pagos.obtener_suscripcion(motor, usuario["id_usuario"])["plan"] == "Premium"


# CP-RF12-01
def test_soporte(con_vehiculo):
    motor, usuario, _ = con_vehiculo
    ok, radicado = soporte.registrar(motor, usuario["id_usuario"], "Otro", "La app no carga el mapa")
    assert ok and radicado == soporte.generar_radicado(datetime.now().year, 1)
    assert not soporte.registrar(motor, usuario["id_usuario"], "Otro", "corto")[0]


# CP-RF04-01: el valor total se calcula si se deja en 0
def test_total_calculado(con_vehiculo):
    motor, _, idv = con_vehiculo
    assert tanqueos.registrar(motor, idv, date(2026, 10, 1), 10, 15800, 0, 45500)["ok"]
    assert tanqueos.historial(motor, idv).iloc[0]["valor_total"] == 158000


# RF-04 (SC-06): registrar un tanqueo olvidado con fecha y km anteriores
def test_tanqueo_olvidado(con_vehiculo):
    motor, _, idv = con_vehiculo
    tanqueos.registrar(motor, idv, date(2026, 10, 1), 10, 16000, 0, 45000)
    tanqueos.registrar(motor, idv, date(2026, 10, 20), 10, 16000, 0, 45800)       # 80 km/gal (hueco)
    r = tanqueos.registrar(motor, idv, date(2026, 10, 10), 10, 16000, 0, 45400)   # el olvidado
    assert r["ok"] and r["rendimiento"] == 40.0
    h = tanqueos.historial(motor, idv)
    assert list(h["rendimiento_km_gal"].fillna(0)) == [0, 40.0, 40.0]               # el siguiente se recalculó
    # fecha anterior pero km que no concuerda
    r = tanqueos.registrar(motor, idv, date(2026, 9, 1), 10, 16000, 0, 45600)
    assert not r["ok"] and "no concuerda" in r["mensaje"]
    # km repetido
    assert not tanqueos.registrar(motor, idv, date(2026, 10, 21), 10, 16000, 0, 45800)["ok"]


# CP-RF13-01 / CP-RF13-02: editar y eliminar tanqueo con recálculo del rendimiento
def test_editar_eliminar_tanqueo(con_vehiculo):
    motor, _, idv = con_vehiculo
    for d, km in [(1, 45000), (10, 45400), (20, 45800)]:
        tanqueos.registrar(motor, idv, date(2026, 10, d), 10, 16000, 0, km)
    h = tanqueos.historial(motor, idv)
    id_medio = int(h.iloc[1]["id_tanqueo"])
    ok, _ = tanqueos.editar(motor, id_medio, date(2026, 10, 10), 8, 16000, 0, 45400)    # galones mal digitados
    assert ok
    h = tanqueos.historial(motor, idv)
    assert h.iloc[1]["rendimiento_km_gal"] == 50.0 and h.iloc[1]["valor_total"] == 128000
    ok, msg = tanqueos.editar(motor, id_medio, date(2026, 10, 25), 8, 16000, 0, 45400)  # fecha no concuerda
    assert not ok and "no concuerda" in msg
    assert tanqueos.eliminar(motor, id_medio)[0]
    h = tanqueos.historial(motor, idv)
    assert len(h) == 2 and h.iloc[1]["rendimiento_km_gal"] == 80.0
    assert not tanqueos.eliminar(motor, 9999)[0]


# CP-RF12-02: historial de solicitudes
def test_historial_soporte(con_vehiculo):
    motor, usuario, _ = con_vehiculo
    soporte.registrar(motor, usuario["id_usuario"], "Otro", "La app no carga el mapa")
    soporte.registrar(motor, usuario["id_usuario"], "Pagos", "No se activó el plan premium")
    assert len(soporte.listar(motor, usuario["id_usuario"])) == 2
