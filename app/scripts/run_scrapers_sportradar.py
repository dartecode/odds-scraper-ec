from app.config.database import SessionLocal
from app.config.logger_config import configurar_logger
from app.models.db.models_db import CasaApuesta
from app.scrapers.betano_scraper import BetanoScraper
from app.scrapers.sorti_scraper import SortiScraper
from app.services.cuotas_service import insertar_cuotas

logger = configurar_logger("run_scrapers_sportradar")

PROVEEDOR_SPORTRADAR_ID = 2

def ejecutar_scrapers_sportradar():
    db = SessionLocal()

    try:
        casas = db.query(CasaApuesta).filter(
            CasaApuesta.activo == True,
            CasaApuesta.proveedor_id == PROVEEDOR_SPORTRADAR_ID,
            CasaApuesta.integracion.in_(["betano", "sorti"])
        ).all()

        logger.info(f"Casas sr encontradas: {len(casas)}")

        for casa in casas:
            logger.info(f"Ejecutando scraper: {casa.nombre} ({casa.integracion})")

            if casa.integracion == "betano":
                scraper = BetanoScraper(casa_apuesta=casa)

            elif casa.integracion == "sorti":
                scraper = SortiScraper(casa_apuesta=casa)

            else:
                logger.warning(f"Integración no soportada: {casa.integracion}")
                continue

            cuotas = scraper.obtener_cuotas()

            if cuotas:
                insertar_cuotas(cuotas)
                logger.info(f"Se insertaron {len(cuotas)} cuotas de {casa.nombre}")
            else:
                logger.warning(f"No se encontraron cuotas para {casa.nombre}")

    except Exception as e:
        logger.exception("Error ejecutando scrapers SportRadar:", e)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    ejecutar_scrapers_sportradar()