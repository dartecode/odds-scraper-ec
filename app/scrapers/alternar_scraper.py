import requests
import os
from decimal import Decimal
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path
from app.models.domain.cuota import CuotaScrapeada
from app.config.logger_config import configurar_logger

logger = configurar_logger("scraper_alternar")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class AltenarScraper:
    BASE_URL = os.getenv("RUTA_ALTERNAR")

    HEADERS = {
        "User-Agent": "Mozilla/5.0"
    }

    MERCADOS_PERMITIDOS = {
        "1x2",
        "total",
        "ambos equipos marcan",
        "doble oportunidad",
    }

    LINEAS_TOTAL_PERMITIDAS = {
        "1.5",
        "2.5",
        "3.5",
    }

    MAPEO_MERCADOS = {
        "1x2": (
            "1X2",
            "Resultado del partido"
        ),

        "total": (
            "OVER_UNDER",
            "Más/Menos goles"
        ),

        "total de goles": (
            "OVER_UNDER",
            "Más/Menos goles"
        ),

        "ambos equipos marcan": (
            "AMBOS_MARCAN",
            "Ambos equipos marcan"
        ),

        "doble oportunidad": (
            "DOBLE_OPORTUNIDAD",
            "Doble oportunidad"
        ),
    }

    def __init__(self, casa_apuesta):
        self.casa_apuesta_id = casa_apuesta.id
        self.casa_apuesta_nombre = casa_apuesta.nombre
        self.integration = casa_apuesta.integracion

    def params_base(self):
        return {
            "culture": "es-ES",
            "timezoneOffset": 300,
            "integration": self.integration,
            "deviceType": 1,
            "numFormat": "en-GB",
            "countryCode": "EC",
        }

    def normalizar(self, texto):
        if texto is None:
            return ""
        return texto.strip().lower().replace("  ", " ")

    def obtener_eventos_liga(self, champ_id=3146, sport_id=66):
        url = f"{self.BASE_URL}/GetEvents"

        params = {
            **self.params_base(),
            "eventCount": 0,
            "sportId": sport_id,
            "champIds": champ_id,
        }

        response = requests.get(
            url,
            params=params,
            headers=self.HEADERS,
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        return data.get("events", [])

    def obtener_detalle_evento(self, event_id):
        url = f"{self.BASE_URL}/GetEventDetails"

        params = {
            **self.params_base(),
            "eventId": event_id,
            "showNonBoosts": "false",
        }

        response = requests.get(
            url,
            params=params,
            headers=self.HEADERS,
            timeout=20
        )

        response.raise_for_status()
        return response.json()

    def mapear_seleccion(self, mercado, seleccion, local, visitante):
        mercado = self.normalizar(mercado)
        seleccion_limpia = self.normalizar(seleccion)
        local_limpio = self.normalizar(local)
        visitante_limpio = self.normalizar(visitante)

        if mercado == "1x2":
            if seleccion_limpia in ["1", local_limpio]:
                return "LOCAL"

            if seleccion_limpia in ["x", "empate"]:
                return "EMPATE"

            if seleccion_limpia in ["2", visitante_limpio]:
                return "VISITANTE"

        if mercado == "total":
            if seleccion_limpia.startswith("más de"):
                return "OVER"
            if seleccion_limpia.startswith("menos de"):
                return "UNDER"

        if mercado in ["total", "total de goles"]:
            if seleccion_limpia.startswith("más de") or seleccion_limpia.startswith("mas de"):
                return "OVER"
            if seleccion_limpia.startswith("menos de"):
                return "UNDER"

        if mercado == "doble oportunidad":
            if seleccion_limpia in [f"{local_limpio} o empate", "1 o empate", "1 o x", "1x"]:
                return "1X"

            if seleccion_limpia in [f"{local_limpio} o {visitante_limpio}", "1 o 2", "12"]:
                return "12"

            if seleccion_limpia in [f"empate o {visitante_limpio}", "empate o 2", "x o 2", "x2"]:
                return "X2"

        raise Exception(
            f"Selección no mapeada: mercado={mercado}, seleccion={seleccion}"
        )

    def extraer_cuotas_evento(self, data):
        cuotas_extraidas = []

        odds_por_id = {
            odd["id"]: odd
            for odd in data.get("odds", [])
        }

        evento_nombre = data.get("name", "")

        if " vs. " not in evento_nombre:
            raise Exception(f"Nombre de evento no válido: {evento_nombre}")

        local, visitante = evento_nombre.split(" vs. ")

        for market in data.get("markets", []):
            mercado_original = market.get("name", "")
            mercado_normalizado = self.normalizar(mercado_original)

            if mercado_normalizado not in self.MERCADOS_PERMITIDOS:
                continue

            if market.get("isBB") is True:
                continue

            mercado_codigo, mercado_nombre = self.MAPEO_MERCADOS[mercado_normalizado]

            for grupo in market.get("desktopOddIds", []):
                for odd_id in grupo:
                    odd = odds_por_id.get(odd_id)

                    if not odd:
                        continue

                    if odd.get("oddStatus") != 0:
                        continue

                    linea = odd.get("sv")

                    if (
                        mercado_normalizado in ["total", "total de goles"]
                        and str(linea) not in self.LINEAS_TOTAL_PERMITIDAS
                    ):
                        continue

                    seleccion_nombre = odd.get("name")

                    seleccion_codigo = self.mapear_seleccion(
                        mercado=mercado_normalizado,
                        seleccion=seleccion_nombre,
                        local=local,
                        visitante=visitante
                    )

                    start_date = data.get("startDate")
                    fecha_partido = datetime.fromisoformat(
                        start_date.replace("Z", "+00:00")
                    ).astimezone(timezone.utc)

                    cuotas_extraidas.append(
                        CuotaScrapeada(
                            equipo_local=local,
                            equipo_visitante=visitante,
                            fecha_partido=fecha_partido,

                            mercado_codigo=mercado_codigo,
                            mercado_nombre=mercado_nombre,

                            seleccion=seleccion_codigo,
                            seleccion_nombre=seleccion_nombre,

                            cuota=Decimal(str(odd.get("price"))),

                            casa_apuesta_id=self.casa_apuesta_id,
                            casa_apuesta_nombre=self.casa_apuesta_nombre,

                            linea=Decimal(str(linea)) if linea is not None else None,
                            fecha_captura=datetime.now(timezone.utc)
                        )
                    )

        return cuotas_extraidas

    def obtener_cuotas(self, champ_id=3146):
        eventos = self.obtener_eventos_liga(champ_id=champ_id)

        todas_las_cuotas = []

        logger.info(f"\nCasa: {self.casa_apuesta_nombre}")
        logger.info(f"Integración: {self.integration}")
        logger.info(f"Eventos encontrados: {len(eventos)}")

        for evento in eventos:
            event_id = evento.get("id")
            nombre = evento.get("name")

            logger.info(f"Procesando {event_id} - {nombre}")

            try:
                detalle = self.obtener_detalle_evento(event_id)
                cuotas = self.extraer_cuotas_evento(detalle)

                logger.info("Cuotas útiles: %s", len(cuotas))

                todas_las_cuotas.extend(cuotas)

            except Exception as e:
                logger.error(f"Error procesando evento {event_id}: {e}")

        return todas_las_cuotas