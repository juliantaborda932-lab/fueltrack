"""FuelTrack — prototipo funcional (Streamlit + Supabase).
Cada pantalla indica su código de interfaz (UI-xx) y los requisitos que cumple."""
from datetime import date

import pandas as pd
import streamlit as st

import alertas
import auth
import pagos
import precios
import reportes
import soporte
import tanqueos
import vehiculos
from actualizar_precios import cargar as cargar_precios
from db import crear_motor, estaciones
from sqlalchemy import func, select

st.set_page_config(page_title="FuelTrack", page_icon="⛽", layout="centered")


@st.cache_resource
def motor_bd():
    motor = crear_motor()
    with motor.connect() as con:
        if con.execute(select(func.count()).select_from(estaciones)).scalar() == 0:
            cargar_precios(motor)   # datos de prueba de estaciones y precios
    return motor


motor = motor_bd()
ss = st.session_state
ss.setdefault("usuario", None)
ss.setdefault("pagina", "Inicio")
ss.setdefault("ticket", None)


def pesos(v):
    return "$" + f"{v:,.0f}".replace(",", ".")


def etiqueta(ui, reqs):
    st.caption(f"Pantalla {ui} · {reqs}")


def elegir_vehiculo(clave):
    df = vehiculos.listar(motor, ss.usuario["id_usuario"])
    if df.empty:
        st.info("Primero registre un vehículo en **Mis vehículos**.")
        if st.button("Ir a Mis vehículos", key=f"ir_{clave}"):
            ss.pagina = "Mis vehículos"
            st.rerun()
        return None
    opciones = {f"{r.placa} · {r.marca} {r.modelo}": r for r in df.itertuples()}
    return opciones[st.selectbox("Vehículo", list(opciones), key=clave)]


# ------------------------------------------------------------------ UI-01
def pantalla_acceso():
    st.title("⛽ FuelTrack")
    st.write("Cada galón cuenta: controla, ahorra y conduce inteligente.")
    etiqueta("UI-01", "RF-01 Registrar cuenta · RF-02 Iniciar sesión")
    t1, t2 = st.tabs(["Iniciar sesión", "Crear cuenta"])
    with t1:
        with st.form("login"):
            correo = st.text_input("Correo electrónico")
            clave = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", type="primary", width="stretch"):
                usuario, msg = auth.iniciar_sesion(motor, correo, clave)
                if usuario:
                    ss.usuario, ss.pagina = usuario, "Inicio"
                    st.rerun()
                st.error(msg)
    with t2:
        with st.form("registro"):
            nombre = st.text_input("Nombre")
            correo = st.text_input("Correo electrónico ")
            clave = st.text_input("Contraseña (mínimo 8 caracteres)", type="password")
            politica = st.checkbox("Acepto la política de tratamiento de datos personales (Ley 1581 de 2012)")
            if st.form_submit_button("Crear cuenta", type="primary", width="stretch"):
                ok, msg = auth.registrar(motor, nombre, correo, clave, politica)
                (st.success if ok else st.error)(msg + (" Ya puede iniciar sesión." if ok else ""))


# ------------------------------------------------------------------ UI-02
def pantalla_inicio():
    st.title(f"Hola, {ss.usuario['nombre'].split()[0]} 👋")
    etiqueta("UI-02", "Menú principal · RNF-05 tanqueo en máximo 3 pantallas")
    accesos = [("⛽ Registrar tanqueo", "Registrar tanqueo"), ("📈 Rendimiento y alertas", "Rendimiento y alertas"),
               ("📍 Precios cercanos", "Precios cercanos"), ("📊 Reportes", "Reportes"),
               ("🚗 Mis vehículos", "Mis vehículos"), ("⭐ Plan premium", "Plan premium")]
    cols = st.columns(2)
    for i, (txt, destino) in enumerate(accesos):
        if cols[i % 2].button(txt, width="stretch", key=f"m{i}"):
            ss.pagina = destino
            st.rerun()
    al = alertas.listar(motor, ss.usuario["id_usuario"])
    if not al.empty:
        st.subheader("Últimas alertas")
        for a in al.head(3).itertuples():
            st.warning(f"{a.placa} · {a.mensaje}")


# ------------------------------------------------------------------ UI-03
def pantalla_vehiculos():
    st.title("🚗 Mis vehículos")
    etiqueta("UI-03", "RF-03 Registrar vehículo")
    with st.form("vehiculo", clear_on_submit=True):
        c1, c2 = st.columns(2)
        placa = c1.text_input("Placa (AAA123)")
        anio = c2.number_input("Año", 1980, date.today().year + 1, 2018)
        marca = c1.text_input("Marca")
        modelo = c2.text_input("Modelo")
        comb = c1.selectbox("Combustible", vehiculos.COMBUSTIBLES)
        km_m = c2.number_input("Mantenimiento cada (km)", 1000, 20000, 5000, step=500)
        if st.form_submit_button("Guardar vehículo", type="primary"):
            ok, msg = vehiculos.registrar(motor, ss.usuario["id_usuario"], placa, marca, modelo, anio, comb, km_m)
            (st.success if ok else st.error)(msg)
    df = vehiculos.listar(motor, ss.usuario["id_usuario"])
    if not df.empty:
        st.dataframe(df[["placa", "marca", "modelo", "anio", "tipo_combustible", "km_mantenimiento"]],
                     hide_index=True, width="stretch")


# ------------------------------------------------------------------ UI-04
def pantalla_tanqueo():
    st.title("⛽ Registrar tanqueo")
    etiqueta("UI-04", "RF-04 Tanqueo manual · RF-05 Leer ticket con OCR")
    veh = elegir_vehiculo("veh_tq")
    if veh is None:
        return
    with st.expander("📷 Escanear ticket (opcional)"):
        modo = st.radio("Foto del ticket", ["Subir imagen", "Tomar foto con la cámara"], horizontal=True)
        if modo == "Tomar foto con la cámara":
            foto = st.camera_input("Tome la foto del ticket")
        else:
            foto = st.file_uploader("Imagen del ticket", type=["jpg", "jpeg", "png"])
        if foto is not None and st.button("Leer ticket"):
            import ocr
            datos = ocr.leer_ticket(foto.getvalue())
            ss.ticket = datos
            if any([datos.galones, datos.precio_galon, datos.valor_total]):
                st.success("Datos leídos. Revíselos y corríjalos si hace falta antes de guardar.")
            else:
                st.warning("No se pudieron leer los datos. Escríbalos a mano.")
    t = ss.ticket
    with st.form("tanqueo"):
        c1, c2 = st.columns(2)
        fecha = c1.date_input("Fecha", date.today(), max_value=date.today(), format="DD/MM/YYYY")
        km = c2.number_input("Kilometraje actual", 0, 2_000_000, 0, step=1)
        gal = c1.number_input("Galones", 0.0, 100.0, float(t.galones or 0.0) if t else 0.0, step=0.1, format="%.3f")
        precio = c2.number_input("Precio por galón ($)", 0.0, 50000.0, float(t.precio_galon or 0.0) if t else 0.0, step=10.0)
        total = st.number_input("Valor total pagado ($)", 0.0, 5_000_000.0,
                                float(t.valor_total or 0.0) if t else 0.0, step=1000.0)
        if st.form_submit_button("Guardar tanqueo", type="primary", width="stretch"):
            r = tanqueos.registrar(motor, veh.id_vehiculo, fecha, gal, precio, total, km,
                                   origen="OCR" if t else "MANUAL", correo_conductor=ss.usuario["correo"])
            if r["ok"]:
                ss.ticket = None
                st.success(r["mensaje"] + (f" Rendimiento: **{r['rendimiento']} km/gal**." if r["rendimiento"] else
                                           " Es el primer tanqueo: el rendimiento se calcula desde el siguiente."))
                for a in r["alertas"]:
                    st.warning("⚠️ " + a)
            else:
                st.error(r["mensaje"])


# ------------------------------------------------------------------ UI-05
def pantalla_rendimiento():
    st.title("📈 Rendimiento y alertas")
    etiqueta("UI-05", "RF-06 Calcular rendimiento · RF-07 Alerta de consumo · RF-08 Mantenimiento")
    veh = elegir_vehiculo("veh_rd")
    if veh is None:
        return
    df = tanqueos.historial(motor, veh.id_vehiculo)
    if df.empty:
        st.info("Aún no hay tanqueos para este vehículo.")
        return
    rend = df["rendimiento_km_gal"].dropna()
    c1, c2, c3 = st.columns(3)
    c1.metric("Último rendimiento", f"{rend.iloc[-1]} km/gal" if not rend.empty else "—")
    c2.metric("Promedio (últ. 5)", f"{round(rend.tail(5).mean(), 1)} km/gal" if not rend.empty else "—")
    c3.metric("Tanqueos", len(df))
    if not rend.empty:
        graf = df.dropna(subset=["rendimiento_km_gal"]).copy()
        graf["fecha"] = pd.to_datetime(graf["fecha"])
        st.line_chart(graf.set_index("fecha")["rendimiento_km_gal"], y_label="km/gal")
    vista = df[["fecha", "kilometraje", "galones", "valor_total", "rendimiento_km_gal", "origen"]].copy()
    vista["valor_total"] = vista["valor_total"].map(pesos)
    st.dataframe(vista.iloc[::-1], hide_index=True, width="stretch")
    al = alertas.listar(motor, ss.usuario["id_usuario"])
    al = al[al["placa"] == veh.placa] if not al.empty else al
    st.subheader("Alertas")
    if al.empty:
        st.success("Sin alertas para este vehículo.")
    for a in al.itertuples():
        (st.error if a.tipo == "CONSUMO" else st.warning)(f"{str(a.fecha)[:16]} · {a.mensaje}")


# ------------------------------------------------------------------ UI-06
def pantalla_precios():
    st.title("📍 Precios cercanos")
    etiqueta("UI-06", "RF-09 Comparar precios · RNF-07 Precios del día")
    veh = elegir_vehiculo("veh_pr")
    if veh is None:
        return
    lat, lon = 6.2442, -75.5812   # centro de Medellín por defecto
    try:
        from streamlit_geolocation import streamlit_geolocation
        st.write("Toque el botón para usar la ubicación GPS del celular:")
        loc = streamlit_geolocation()
        if loc and loc.get("latitude"):
            lat, lon = loc["latitude"], loc["longitude"]
            st.caption(f"Ubicación GPS: {lat:.4f}, {lon:.4f}")
    except Exception:
        pass
    with st.expander("Ubicación manual"):
        lat = st.number_input("Latitud", value=float(lat), format="%.4f")
        lon = st.number_input("Longitud", value=float(lon), format="%.4f")
    df = precios.estaciones_cercanas(precios.ultimos_precios(motor, veh.tipo_combustible), lat, lon)
    st.write(f"Estaciones a máximo {precios.RADIO_KM:.0f} km · **{veh.tipo_combustible}**, de menor a mayor precio:")
    if df.empty:
        st.info("No hay estaciones a 5 km.")
        return
    import folium
    from streamlit_folium import st_folium
    mapa = folium.Map(location=[lat, lon], zoom_start=13)
    folium.Marker([lat, lon], tooltip="Usted está aquí", icon=folium.Icon(color="red")).add_to(mapa)
    for r in df.itertuples():
        folium.Marker([r.latitud, r.longitud], tooltip=f"{r.nombre}: {pesos(r.precio_galon)}",
                      icon=folium.Icon(color="green" if r.Index == 0 else "blue")).add_to(mapa)
    st_folium(mapa, height=320, width="stretch", returned_objects=[])
    vista = df[["nombre", "precio_galon", "distancia_km", "fecha_actualizacion"]].copy()
    vista["precio_galon"] = vista["precio_galon"].map(pesos)
    vista["fecha_actualizacion"] = pd.to_datetime(vista["fecha_actualizacion"]).dt.strftime("%d/%m/%Y %H:%M")
    vista.columns = ["Estación", "Precio/galón", "Distancia (km)", "Actualizado"]
    st.dataframe(vista, hide_index=True, width="stretch")


# ------------------------------------------------------------------ UI-07
def pantalla_reportes():
    st.title("📊 Reportes")
    etiqueta("UI-07", "RF-10 Reporte mensual y PDF")
    veh = elegir_vehiculo("veh_rp")
    if veh is None:
        return
    df = tanqueos.historial(motor, veh.id_vehiculo)
    if df.empty:
        st.info("Aún no hay tanqueos para este vehículo.")
        return
    meses = sorted(pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m").unique(), reverse=True)
    mes = st.selectbox("Mes", meses)
    rep = reportes.resumen_mes(df, mes)
    c1, c2, c3 = st.columns(3)
    c1.metric("Gasto total", pesos(rep.gasto_total))
    c2.metric("Galones", f"{rep.galones:.1f}")
    c3.metric("Rendimiento promedio", f"{rep.rendimiento_promedio} km/gal" if rep.rendimiento_promedio else "—")
    st.bar_chart(reportes.gasto_por_semana(rep).set_index("Semana")["Gasto"], y_label="Gasto ($)")
    st.download_button("⬇️ Descargar PDF", reportes.exportar_pdf(rep, veh.placa, ss.usuario["nombre"]),
                       file_name=f"FuelTrack_{veh.placa}_{mes}.pdf", mime="application/pdf", type="primary")


# ------------------------------------------------------------------ UI-08
def pantalla_premium():
    st.title("⭐ Plan premium")
    etiqueta("UI-08", "RF-11 Suscribirse al plan premium")
    sus = pagos.obtener_suscripcion(motor, ss.usuario["id_usuario"])
    st.metric("Plan actual", sus["plan"])
    st.table(pd.DataFrame({"Función": ["Registro de tanqueos y rendimiento", "Alertas de consumo", "Comparar precios",
                                       "Varios vehículos y reportes PDF ilimitados"],
                           "Gratis": ["✔", "✔", "✔", "1 vehículo"], "Premium": ["✔", "✔", "✔", "✔"]}))
    if sus["plan"] == "Premium":
        st.success("Su plan Premium está activo.")
        return
    st.write(f"Valor: **{pesos(pagos.VALOR_PREMIUM)} / mes**. El pago se hace en la pasarela Wompi; FuelTrack no guarda datos de tarjetas.")
    if st.button("Pagar con Wompi", type="primary"):
        ss.pago = pagos.iniciar_pago(motor, ss.usuario["id_usuario"])
    if ss.get("pago"):
        st.info(f"Referencia de pago: **{ss.pago['referencia']}** · {pesos(ss.pago['valor'])}")
        st.caption("Prototipo en modo de pruebas (sandbox): simule la respuesta de la pasarela.")
        c1, c2 = st.columns(2)
        if c1.button("Simular pago aprobado"):
            pagos.confirmar_pago(motor, ss.pago["referencia"], True)
            ss.pago = None
            st.rerun()
        if c2.button("Simular pago rechazado"):
            pagos.confirmar_pago(motor, ss.pago["referencia"], False)
            ss.pago = None
            st.error("Pago rechazado. Su plan no cambió.")


# ------------------------------------------------------------------ UI-09
def pantalla_soporte():
    st.title("💬 Soporte")
    etiqueta("UI-09", "RF-12 Solicitar soporte")
    with st.form("soporte", clear_on_submit=True):
        cat = st.selectbox("Categoría", soporte.CATEGORIAS)
        desc = st.text_area("Describa el problema")
        if st.form_submit_button("Enviar solicitud", type="primary"):
            ok, msg = soporte.registrar(motor, ss.usuario["id_usuario"], cat, desc)
            if ok:
                st.success(f"Solicitud registrada con el radicado **{msg}**. Estado: Abierta.")
            else:
                st.error(msg)


PAGINAS = {"Inicio": pantalla_inicio, "Mis vehículos": pantalla_vehiculos, "Registrar tanqueo": pantalla_tanqueo,
           "Rendimiento y alertas": pantalla_rendimiento, "Precios cercanos": pantalla_precios,
           "Reportes": pantalla_reportes, "Plan premium": pantalla_premium, "Soporte": pantalla_soporte}

if ss.usuario is None:
    pantalla_acceso()
else:
    with st.sidebar:
        st.markdown(f"**⛽ FuelTrack**  \n{ss.usuario['nombre']}")
        ss.pagina = st.radio("Menú", list(PAGINAS), index=list(PAGINAS).index(ss.pagina))
        if st.button("Cerrar sesión"):
            ss.usuario, ss.pagina = None, "Inicio"
            st.rerun()
    PAGINAS[ss.pagina]()
