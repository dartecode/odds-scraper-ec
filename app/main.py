from apscheduler.schedulers.blocking import BlockingScheduler
from app.scripts.run_scrapers_altenar import ejecutar_scrapers_altenar
from app.scripts.run_scrapers_sportradar import ejecutar_scrapers_sportradar
from app.services.limpieza_service import limpiar_cuotas_antiguas

def ejecutar_scraping():
    print("===================================")
    print("INICIANDO SCRAPING")
    print("===================================")

    try:
        ejecutar_scrapers_altenar()
        #ejecutar_scrapers_sportradar()

    except Exception as e:
        print("Error general:", e)

    print("===================================")
    print("SCRAPING FINALIZADO")
    print("===================================")


if __name__ == "__main__":
    scheduler = BlockingScheduler()

    scheduler.add_job(
        ejecutar_scraping,
        "interval",
        hours=1
    )

    scheduler.add_job(
        limpiar_cuotas_antiguas,
        "cron",
        hour=3
    )

    ejecutar_scraping()

    print("Scheduler iniciado. Scraping cada 1 hora...")

    scheduler.start()