from app.config.database import SessionLocal
from app.models.db.models_db import CasaApuesta
from app.scrapers.alternar_scraper import AltenarScraper
from app.services.cuotas_service import insertar_cuotas
from app.config.logger_config import configurar_logger

logger = configurar_logger("run_scrapers_alternar")

PROVEEDOR_ALTENAR_ID = 1

def ejecutar_scrapers_altenar():
    db = SessionLocal()

    try:
        casas = db.query(CasaApuesta).filter(
            CasaApuesta.activo == True,
            CasaApuesta.proveedor_id == PROVEEDOR_ALTENAR_ID,
            CasaApuesta.integracion.isnot(None)
        ).all()

        logger.info("Casas Altenar encontradas: %s", {len(casas)})

        for casa in casas:
            scraper = AltenarScraper(casa_apuesta=casa)

            cuotas = scraper.obtener_cuotas(champ_id=3146)

            if cuotas:
                insertar_cuotas(cuotas)
                logger.info(f"Se insertaron {len(cuotas)} cuotas de {casa.nombre}")

    except Exception as e:
        logger.exception(f"Error ejecutando scrapers Altenar:", {e})
        raise

    finally:
        db.close()