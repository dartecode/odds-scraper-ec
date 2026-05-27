from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class CuotaScrapeada:
    equipo_local: str
    equipo_visitante: str
    fecha_partido: datetime

    mercado_codigo: str
    mercado_nombre: str

    seleccion: str
    seleccion_nombre: str

    cuota: Decimal

    casa_apuesta_nombre: str
    casa_apuesta_id: int

    linea: Optional[Decimal] = None
    fecha_captura: Optional[datetime] = None