import time
from app.scripts.run_scrapers_altenar import ejecutar_scrapers_altenar
from app.scripts.run_scrapers_sportradar import ejecutar_scrapers_sportradar
from app.services.limpieza_service import limpiar_cuotas_antiguas

def ejecutar_proceso():
    print("===================================")
    print("INICIANDO SCRAPING")
    print("===================================")

    try:
        ejecutar_scrapers_altenar()
        ejecutar_scrapers_sportradar()
        limpiar_cuotas_antiguas()

    except Exception as e:
        print("Error general:", e)

    print("===================================")
    print("SCRAPING FINALIZADO")
    print("===================================")


def main():
    while True:
        ejecutar_proceso()

        print("Esperando 5 minutos antes de volver a ejecutar...")
        time.sleep(300)


if __name__ == "__main__":
    main()