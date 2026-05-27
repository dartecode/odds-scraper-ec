from sqlalchemy import text
from app.config.database import SessionLocal
from app.config.logger_config import configurar_logger

logger = configurar_logger("scraper_limpieza_cuota")

def limpiar_cuotas_antiguas():
    db = SessionLocal()

    try:
        db.execute(text("""
            DELETE FROM cuota
            WHERE fecha_captura < NOW() - INTERVAL '8 days'
        """))

        db.commit()

        logger.info("Cuotas antiguas eliminadas")

    except Exception as e:
        logger.error("Error limpiando cuotas:", e)

    finally:
        db.close()