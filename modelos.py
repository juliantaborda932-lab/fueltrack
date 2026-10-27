"""Clases del dominio (diagrama de clases y diccionario ADOO-POO)."""
from dataclasses import dataclass, field
from datetime import date, datetime
from math import asin, cos, radians, sin, sqrt
from typing import ClassVar, List, Optional

@dataclass
class Ubicacion:
    latitud: float
    longitud: float


@dataclass
class PrecioCombustible:
    tipo_combustible: str
    precio_galon: float
    fecha_actualizacion: datetime


@dataclass
class Estacion:
    id_estacion: int
    nombre: str
    ubicacion: Ubicacion
    aliada: bool = False
    precios: List[PrecioCombustible] = field(default_factory=list)
    RADIO_TIERRA_KM: ClassVar[float] = 6371.0   # variable de clase (compartida)

    def distancia_km(self, desde: Ubicacion) -> float:
        """Distancia en línea recta (fórmula de Haversine)."""
        lat1, lon1 = radians(desde.latitud), radians(desde.longitud)
        lat2, lon2 = radians(self.ubicacion.latitud), radians(self.ubicacion.longitud)
        a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
        return 2 * Estacion.RADIO_TIERRA_KM * asin(sqrt(a))


@dataclass
class DatosTicket:
    galones: Optional[float] = None
    precio_galon: Optional[float] = None
    valor_total: Optional[float] = None


@dataclass
class Tanqueo:
    fecha: date
    galones: float
    precio_galon: float
    valor_total: float
    kilometraje: int
    origen: str = "MANUAL"
    rendimiento_km_gal: Optional[float] = None
    id_tanqueo: Optional[int] = None
    estacion: Optional[Estacion] = None

    def validar_kilometraje(self, anterior: Optional["Tanqueo"]) -> bool:
        return anterior is None or self.kilometraje > anterior.kilometraje

    def calcular_rendimiento(self, anterior: Optional["Tanqueo"]) -> Optional[float]:
        if anterior is None or self.galones <= 0:
            return None
        self.rendimiento_km_gal = round((self.kilometraje - anterior.kilometraje) / self.galones, 2)
        return self.rendimiento_km_gal


@dataclass
class Alerta:
    tipo: str          # CONSUMO o MANTENIMIENTO
    mensaje: str
    fecha: datetime = field(default_factory=datetime.now)

    def mostrar(self) -> str:
        return f"{self.fecha:%d/%m/%Y} · {self.mensaje}"


@dataclass
class AlertaConsumo(Alerta):
    """Herencia: alerta que se muestra en pantalla (RF-07)."""
    diferencia_pct: int = 0
    UMBRAL: ClassVar[float] = 0.15


@dataclass
class AlertaMantenimiento(Alerta):
    """Herencia: alerta que además se envía por correo (RF-08)."""
    kilometraje: int = 0

    def enviar_correo(self, destino: str) -> bool:
        from alertas import enviar_correo
        return enviar_correo(destino, "Mantenimiento pendiente", self.mensaje)


@dataclass
class Vehiculo:
    COMBUSTIBLES: ClassVar[tuple] = ("Corriente", "Extra", "Diésel")   # variable de clase
    placa: str
    marca: str
    modelo: str
    anio: int
    tipo_combustible: str
    km_mantenimiento: int = 5000
    id_vehiculo: Optional[int] = None
    tanqueos: List[Tanqueo] = field(default_factory=list)

    def rendimiento_promedio(self, n: int = 5) -> Optional[float]:
        valores = [t.rendimiento_km_gal for t in self.tanqueos if t.rendimiento_km_gal]
        ultimos = valores[-n:]
        return round(sum(ultimos) / len(ultimos), 2) if ultimos else None

    def requiere_mantenimiento(self, km_anterior: int, km_actual: int) -> bool:
        """True si entre los dos kilometrajes se cruzó un múltiplo del intervalo."""
        return km_actual // self.km_mantenimiento > km_anterior // self.km_mantenimiento


@dataclass
class ReporteMensual:
    mes: str
    gasto_total: float = 0.0
    galones: float = 0.0
    rendimiento_promedio: Optional[float] = None
    tanqueos: List[Tanqueo] = field(default_factory=list)


@dataclass
class Pago:
    referencia_pasarela: str
    valor: float
    estado: str = "PENDIENTE"


@dataclass
class Suscripcion:
    plan: str = "Gratis"
    estado: str = "Activa"
    pagos: List[Pago] = field(default_factory=list)

    def activar(self):
        self.plan, self.estado = "Premium", "Activa"


@dataclass
class SolicitudSoporte:
    radicado: str
    categoria: str
    descripcion: str
    estado: str = "Abierta"


@dataclass
class Usuario:
    nombre: str
    correo: str
    acepta_politica: bool
    id_usuario: Optional[int] = None
    intentos_fallidos: int = 0
    vehiculos: List[Vehiculo] = field(default_factory=list)
