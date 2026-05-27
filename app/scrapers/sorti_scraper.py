import os
import requests
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from app.models.domain.cuota import CuotaScrapeada
from app.config.logger_config import configurar_logger

logger = configurar_logger("scraper_sorti")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class SortiScraper:
    API_URL = os.getenv("RUTA_SORTI")

    MERCADOS_PERMITIDOS = {
        1: "1X2",
        10: "DOBLE_OPORTUNIDAD",
        18: "OVER_UNDER",
        29: "AMBOS_MARCAN",
    }

    OUTCOMES = {
        1: {
            "1": "LOCAL",
            "2": "EMPATE",
            "3": "VISITANTE",
        },
        10: {
            "9": "1X",
            "10": "12",
            "11": "X2",
        },
        18: {
            "12": "OVER",
            "13": "UNDER",
        },
        29: {
            "74": "SI",
            "76": "NO",
        },
    }

    LINEAS_OVER_UNDER_PERMITIDAS = [
        Decimal("1.5"),
        Decimal("2.5"),
        Decimal("3.5"),
    ]

    def __init__(self, casa_apuesta):
        self.casa_apuesta = casa_apuesta

    def obtener_cuotas(self):
        eventos = self._obtener_eventos()

        logger.info(f"Partidos Sorti encontrados: {len(eventos)}")

        todas_las_cuotas = []

        for evento in eventos:
            cuotas = self._extraer_cuotas_partido(evento)
            todas_las_cuotas.extend(cuotas)

        return todas_las_cuotas

    def _obtener_eventos(self):
        params = {
            "sportId": "sr:sport:1",
            "eventType": "SoccerEvent",
            "tournamentId": "sr:tournament:16",
            "startDate": "Thu May 21 2026 00:00:00 GMT-0500",
            "endDate": "Thu May 20 2027 23:59:59 GMT-0500",
            "limit": 50,
            "marketId": [1, 10, 18, 29],
            "statusesEventSport": ["Live", "NotStarted"],
        }

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Origin": "https://www.sorti.ec",
            "Referer": "https://www.sorti.ec/",
        }

        try:
            response = requests.get(
                self.API_URL,
                params=params,
                headers=headers,
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

            if not isinstance(data, list):
                logger.warning("Respuesta Sorti no es lista")
                return []

            return data

        except Exception as e:
            logger.error("Error leyendo eventos Sorti:", e)
            return []

    def _obtener_nombre_outcome(self, outcome):
        nombre = outcome.get("outcomeName")

        if isinstance(nombre, dict):
            return nombre.get("es") or nombre.get("en")

        return nombre

    def _obtener_equipos_desde_1x2(self, evento):
        for market in evento.get("markets", []):
            if market.get("marketId") != 1:
                continue

            for line in market.get("marketLines", []):
                local = None
                visitante = None

                for outcome in line.get("outcomes", []):
                    outcome_id = str(outcome.get("_id"))
                    nombre = self._obtener_nombre_outcome(outcome)

                    if outcome_id == "1":
                        local = nombre
                    elif outcome_id == "3":
                        visitante = nombre

                if local and visitante:
                    return local, visitante

        return None, None

    def _obtener_fecha_partido(self, evento):
        scheduled = evento.get("scheduled")

        if not scheduled:
            return None

        try:
            return datetime.fromisoformat(
                scheduled.replace("Z", "+00:00")
            ).astimezone(timezone.utc)

        except Exception:
            return None

    def _extraer_linea(self, specifiers):
        if not specifiers:
            return None

        if "=" not in specifiers:
            return None

        _, valor = specifiers.split("=", 1)

        try:
            return Decimal(valor)
        except InvalidOperation:
            return None

    def _extraer_cuotas_partido(self, evento):
        local, visitante = self._obtener_equipos_desde_1x2(evento)

        if not local or not visitante:
            logger.error(f"No se pudieron obtener equipos Sorti:", {evento.get("eventId")})
            return []

        fecha_partido = self._obtener_fecha_partido(evento)

        cuotas = []

        for market in evento.get("markets", []):
            market_id = market.get("marketId")
            mercado_codigo = self.MERCADOS_PERMITIDOS.get(market_id)

            if not mercado_codigo:
                continue

            mercado_nombre = market.get("marketName", {})

            if isinstance(mercado_nombre, dict):
                mercado_nombre = mercado_nombre.get("es") or mercado_nombre.get("en")

            for line in market.get("marketLines", []):
                if line.get("status") != "Active":
                    continue

                linea = self._extraer_linea(line.get("specifiers"))

                if mercado_codigo == "OVER_UNDER":
                    if linea not in self.LINEAS_OVER_UNDER_PERMITIDAS:
                        continue

                for outcome in line.get("outcomes", []):
                    if not outcome.get("active"):
                        continue

                    outcome_id = str(outcome.get("_id"))
                    seleccion = self.OUTCOMES.get(market_id, {}).get(outcome_id)

                    if not seleccion:
                        continue

                    odds = outcome.get("odds")

                    if odds is None:
                        continue

                    cuota = CuotaScrapeada(
                        equipo_local=local,
                        equipo_visitante=visitante,

                        fecha_partido=fecha_partido,

                        mercado_codigo=mercado_codigo,
                        mercado_nombre=mercado_nombre,

                        seleccion=seleccion,
                        seleccion_nombre=self._obtener_nombre_outcome(outcome),

                        cuota=Decimal(str(odds)),
                        linea=linea,

                        casa_apuesta_nombre=self.casa_apuesta.nombre,
                        casa_apuesta_id=self.casa_apuesta.id,

                        fecha_captura=datetime.now(timezone.utc),
                    )

                    cuotas.append(cuota)

        return cuotas