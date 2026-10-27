"""Lectura del ticket con Tesseract OCR (RF-05)."""
import io
import re

from modelos import DatosTicket


def _numero(texto, volumen=False):
    """Convierte '16.250' o '16,250.00' o '10,5' a float. En volúmenes la coma es decimal."""
    t = texto.strip().replace("$", "").replace(" ", "")
    if volumen and "," in t and "." not in t:
        t = t.replace(",", ".")
    elif re.search(r"\d+\.\d{3}(\.|$)", t) and "," not in t:      # 16.250 -> miles con punto
        t = t.replace(".", "")
    elif "," in t and "." in t:                                 # 16,250.00
        t = t.replace(",", "")
    elif re.search(r",\d{3}$", t):                              # 160,000
        t = t.replace(",", "")
    else:
        t = t.replace(",", ".")                                 # 10,5
    try:
        return float(t)
    except ValueError:
        return None


def extraer_datos(texto: str) -> DatosTicket:
    """Busca en el texto del ticket los galones, el precio por galón y el total."""
    datos = DatosTicket()
    lineas = [l.lower() for l in texto.splitlines()]
    num = r"\$?\s*([\d.,]+)"
    for l in lineas:
        if datos.galones is None and re.search(r"gal(ones|on)?\b|cantidad|volumen", l) and "precio" not in l and "/" not in l:
            m = re.search(num, l.split(":")[-1])
            if m:
                datos.galones = _numero(m.group(1), volumen=True)
        if datos.precio_galon is None and re.search(r"precio|p/gal|\$/gal|valor unit", l):
            m = re.search(num, l.split(":")[-1])
            if m:
                datos.precio_galon = _numero(m.group(1))
        if datos.valor_total is None and re.search(r"total", l):
            m = re.search(num, l.split(":")[-1])
            if m:
                datos.valor_total = _numero(m.group(1))
    return datos


def leer_ticket(imagen_bytes: bytes) -> DatosTicket:
    import pytesseract
    from PIL import Image
    img = Image.open(io.BytesIO(imagen_bytes)).convert("L")
    try:
        texto = pytesseract.image_to_string(img, lang="spa")
    except pytesseract.TesseractError:
        texto = pytesseract.image_to_string(img)
    return extraer_datos(texto)
