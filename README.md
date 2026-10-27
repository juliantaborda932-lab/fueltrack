# ⛽ FuelTrack — prototipo funcional

Aplicación web para el celular que registra los tanqueos, calcula el rendimiento (km/galón), genera alertas de consumo, compara precios de estaciones cercanas y genera reportes mensuales en PDF.
Proyecto de clase de Ingeniería de Software II — Institución Universitaria Pascual Bravo.

## Tecnologías (todas gratuitas)
- Python 3.11 + Streamlit (interfaz) — publicada en Streamlit Community Cloud
- Supabase (PostgreSQL) — base de datos; SQLite local si no hay secretos
- Tesseract OCR — lectura del ticket · OpenStreetMap + Folium — mapa
- GitHub Actions — actualización diaria de precios y pruebas automáticas (pytest)

## Ejecutar en el computador
```bash
pip install -r requirements.txt
streamlit run app.py          # usa fueltrack.db (SQLite) si no hay DATABASE_URL
pytest --cov=rendimiento --cov=alertas --cov=tanqueos
```
Para leer tickets en local se necesita Tesseract instalado (Windows: instalador de UB Mannheim; Linux: `sudo apt install tesseract-ocr tesseract-ocr-spa`).

## Publicar (Supabase + Streamlit Community Cloud)
1. En Supabase cree un proyecto gratuito y ejecute `schema.sql` en **SQL Editor** (opcional: la app crea las tablas sola).
2. Copie la cadena de conexión (Connect › Connection string › URI, modo *Transaction pooler*) y cámbiele el inicio a `postgresql+psycopg2://`.
3. Suba esta carpeta a un repositorio de GitHub (sin `.streamlit/secrets.toml`).
4. En share.streamlit.io cree la app apuntando a `app.py` y en **Settings › Secrets** pegue el contenido de `.streamlit/secrets.toml.example` con sus datos.
5. En GitHub › Settings › Secrets and variables › Actions cree el secreto `DATABASE_URL` para la tarea diaria de precios.

## Módulos y requisitos
| Archivo | Requisitos |
|---|---|
| auth.py | RF-01, RF-02, RNF-03 |
| vehiculos.py | RF-03 |
| tanqueos.py | RF-04 (usa rendimiento.py y alertas.py) |
| ocr.py | RF-05 |
| rendimiento.py | RF-06 |
| alertas.py | RF-07, RF-08 |
| precios.py, actualizar_precios.py | RF-09, RNF-07 |
| reportes.py | RF-10 |
| pagos.py | RF-11 (modo de pruebas de la pasarela) |
| soporte.py | RF-12 |
| modelos.py | Clases del diagrama de clases (ADOO-POO) |
| db.py, schema.sql | Modelo físico (diagrama entidad-relación) |

Los precios de `data/precios_aliadas.csv` son **datos de prueba**.
