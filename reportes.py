"""Reporte mensual y PDF (RF-10)."""
import pandas as pd
from fpdf import FPDF

from modelos import ReporteMensual


def resumen_mes(df: pd.DataFrame, mes: str) -> ReporteMensual:
    """mes en formato AAAA-MM."""
    rep = ReporteMensual(mes=mes)
    if df.empty:
        return rep
    d = df.copy()
    d["fecha"] = pd.to_datetime(d["fecha"])
    d = d[d["fecha"].dt.strftime("%Y-%m") == mes]
    if d.empty:
        return rep
    rep.gasto_total = float(d["valor_total"].sum())
    rep.galones = round(float(d["galones"].sum()), 2)
    rend = d["rendimiento_km_gal"].dropna()
    rep.rendimiento_promedio = round(float(rend.mean()), 2) if not rend.empty else None
    rep.tanqueos = d.to_dict("records")
    return rep


def gasto_por_semana(rep: ReporteMensual) -> pd.DataFrame:
    if not rep.tanqueos:
        return pd.DataFrame(columns=["Semana", "Gasto"])
    d = pd.DataFrame(rep.tanqueos)
    d["Semana"] = "Semana " + ((pd.to_datetime(d["fecha"]).dt.day - 1) // 7 + 1).astype(str)
    return d.groupby("Semana", as_index=False)["valor_total"].sum().rename(columns={"valor_total": "Gasto"})


def pesos(v):
    return "$" + f"{v:,.0f}".replace(",", ".")


def exportar_pdf(rep: ReporteMensual, placa: str, nombre: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "FuelTrack - Reporte mensual", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Conductor: {nombre}   Vehiculo: {placa}   Mes: {rep.mes}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    for etiqueta, valor in [("Gasto total", pesos(rep.gasto_total)), ("Galones consumidos", f"{rep.galones:.2f}"),
                            ("Rendimiento promedio", f"{rep.rendimiento_promedio} km/gal" if rep.rendimiento_promedio else "N/D"),
                            ("Numero de tanqueos", str(len(rep.tanqueos)))]:
        pdf.cell(70, 8, etiqueta, border=1)
        pdf.cell(60, 8, valor, border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    for h, w in [("Fecha", 30), ("Km", 25), ("Galones", 25), ("Valor", 35), ("km/gal", 25), ("Origen", 25)]:
        pdf.cell(w, 7, h, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 10)
    for t in rep.tanqueos:
        fila = [str(t["fecha"])[:10], f"{t['kilometraje']}", f"{t['galones']:.2f}", pesos(t["valor_total"]),
                f"{t['rendimiento_km_gal']}" if pd.notna(t["rendimiento_km_gal"]) else "-", t["origen"]]
        for v, w in zip(fila, [30, 25, 25, 35, 25, 25]):
            pdf.cell(w, 7, v, border=1)
        pdf.ln()
    return bytes(pdf.output())
