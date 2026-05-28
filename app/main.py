from app.scripts.run_scrapers_altenar import ejecutar_scrapers_altenar
from app.scripts.run_scrapers_sportradar import ejecutar_scrapers_sportradar
from app.services.limpieza_service import limpiar_cuotas_antiguas

def main():
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


if __name__ == "__main__":
    main()