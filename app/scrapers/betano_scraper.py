import json
import os
from decimal import Decimal
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path
from playwright.sync_api import sync_playwright
from app.models.domain.cuota import CuotaScrapeada
from app.config.logger_config import configurar_logger

logger = configurar_logger("scraper_sorti")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class BetanoScraper:
    BASE_URL = "https://ec.betano.com"

    LIGA_API = os.getenv("BETANO_LIGA_API")

    MERCADOS_PERMITIDOS = {
        "MRES": "1X2",
        "HCTG": "OVER_UNDER",
        "BTSC": "AMBOS_MARCAN",
        "DBLC": "DOBLE_OPORTUNIDAD",
    }

    LINEAS_OVER_UNDER_PERMITIDAS = [
        Decimal("1.5"),
        Decimal("2.5"),
        Decimal("3.5"),
    ]

    def __init__(self, casa_apuesta):
        self.casa_apuesta = casa_apuesta

    def obtener_cuotas(self):
        todas_las_cuotas = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="es-EC",
                timezone_id="America/Guayaquil",
                extra_http_headers={
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "es-EC,es;q=0.9,en;q=0.8",
                    "Referer": "https://ec.betano.com/sport/futbol/copa-mundial/copa-mundial-2026/493g/",
                },
            )

            page = context.new_page()

            json_liga = self._leer_json(page, self.LIGA_API)

            if not json_liga:
                context.close()
                browser.close()
                return []

            eventos = self._obtener_eventos_liga(json_liga)

            logger.info(f"Partidos Betano encontrados: {len(eventos)}")

            for evento in eventos:
                api_partido = self._construir_api_partido(evento)

                logger.info(f"Leyendo partido Betano:", {api_partido})

                json_partido = self._leer_json(page, api_partido)

                if not json_partido:
                    continue

                cuotas = self._extraer_cuotas_partido(json_partido)

                logger.info(f"Cuotas extraídas del partido:", {len(cuotas)})

                todas_las_cuotas.extend(cuotas)

            context.close()
            browser.close()

        return todas_las_cuotas

    def _leer_json(self, page, url):
        try:
            if not url:
                logger.warning("URL Betano vacía o None")
                return None

            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)

            status = response.status if response else None
            final_url = page.url

            contenido = page.locator("body").inner_text().strip()

            if not contenido:
                logger.warning("Respuesta vacía Betano:", url)
                return None

            if not contenido.startswith("{"):
                logger.error(f"No llegó JSON Betano:", {url})
                logger.warning(f"Inicio respuesta:", {contenido[:300]})
                return None

            return json.loads(contenido)

        except Exception as e:
            logger.error(f"Error leyendo JSON Betano:", {e})
            return None

    def _buscar_eventos(self, obj, eventos):
        if isinstance(obj, dict):
            if "id" in obj and "url" in obj and "participants" in obj:
                eventos.append(obj)

            for value in obj.values():
                self._buscar_eventos(value, eventos)

        elif isinstance(obj, list):
            for item in obj:
                self._buscar_eventos(item, eventos)

    def _obtener_eventos_liga(self, json_liga):
        eventos = []
        self._buscar_eventos(json_liga, eventos)

        eventos_unicos = {}

        for evento in eventos:
            event_id = str(evento.get("id"))

            if event_id and evento.get("url"):
                eventos_unicos[event_id] = evento

        return list(eventos_unicos.values())

    def _construir_api_partido(self, evento):
        event_url = evento["url"]

        if not event_url.startswith("/"):
            event_url = "/" + event_url

        return f"{self.BASE_URL}/api{event_url}?req=s,stnf,c,mb,mbl"

    def _normalizar_seleccion(self, nombre, mercado_codigo, local=None, visitante=None):
        nombre_original = nombre or ""
        nombre = nombre_original.strip().lower()

        local = local.strip().lower() if local else ""
        visitante = visitante.strip().lower() if visitante else ""

        if mercado_codigo == "1X2":
            return {
                "1": "LOCAL",
                "x": "EMPATE",
                "2": "VISITANTE",
            }.get(nombre)

        if mercado_codigo == "OVER_UNDER":
            if nombre.startswith("más") or nombre.startswith("mas") or nombre.lower() == "over":
                return "OVER"

            if nombre.startswith("menos") or nombre.lower() == "under":
                return "UNDER"

        if mercado_codigo == "AMBOS_MARCAN":
            return {
                "sí": "SI",
                "si": "SI",
                "no": "NO",
            }.get(nombre)

        if mercado_codigo == "DOBLE_OPORTUNIDAD":
            if nombre in ["1x", "1 o x", "1 or x"]:
                return "1X"

            if nombre in ["12", "1 o 2", "1 or 2"]:
                return "12"

            if nombre in ["x2", "x o 2", "x or 2"]:
                return "X2"

            if local in nombre and "empate" in nombre:
                return "1X"

            if local in nombre and visitante in nombre:
                return "12"

            if visitante in nombre and "empate" in nombre:
                return "X2"

        return None

    def _extraer_cuotas_partido(self, json_data):
        event = json_data["data"]["event"]

        local = event["participants"][0]["name"]
        visitante = event["participants"][1]["name"]
        fecha_partido = datetime.fromtimestamp(event["startTime"] / 1000, tz=timezone.utc)

        cuotas = []

        for market in event.get("markets", []):
            market_type = market.get("type")
            market_name = market.get("name")

            mercado_codigo = self.MERCADOS_PERMITIDOS.get(market_type)

            if not mercado_codigo:
                continue

            mercado_nombre = market.get("name")

            for sel in market.get("selections", []):
                if "price" not in sel:
                    continue

                nombre_seleccion = sel.get("name", "")
                nombre_completo = sel.get("fullName", "")

                seleccion = self._normalizar_seleccion(
                    nombre_seleccion,
                    mercado_codigo,
                    local,
                    visitante,
                )

                if not seleccion and nombre_completo:
                    seleccion = self._normalizar_seleccion(
                        nombre_completo,
                        mercado_codigo,
                        local,
                        visitante,
                    )

                linea = None

                if mercado_codigo == "OVER_UNDER":
                    linea = Decimal(str(sel.get("handicap")))

                    if linea not in self.LINEAS_OVER_UNDER_PERMITIDAS:
                        continue

                cuota = CuotaScrapeada(
                    equipo_local=local,
                    equipo_visitante=visitante,

                    fecha_partido=fecha_partido,

                    mercado_codigo=mercado_codigo,
                    mercado_nombre=mercado_nombre,

                    seleccion=seleccion,
                    seleccion_nombre=sel.get("fullName") or sel.get("name"),

                    cuota=Decimal(str(sel["price"])),
                    linea=linea,

                    casa_apuesta_nombre=self.casa_apuesta.nombre,
                    casa_apuesta_id=self.casa_apuesta.id,

                    fecha_captura=datetime.now(timezone.utc),
                )

                cuotas.append(cuota)

        return cuotas