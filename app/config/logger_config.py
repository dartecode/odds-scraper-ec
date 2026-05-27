import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

FECHA_EJECUCION = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = LOG_DIR / f"scraper_{FECHA_EJECUCION}.log"

def configurar_logger(nombre: str = "scrapers"):
    logger = logging.getLogger(nombre)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    archivo_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    archivo_handler.setLevel(logging.INFO)
    archivo_handler.setFormatter(formato)

    consola_handler = logging.StreamHandler()
    consola_handler.setLevel(logging.INFO)
    consola_handler.setFormatter(formato)

    logger.addHandler(archivo_handler)
    logger.addHandler(consola_handler)

    return logger