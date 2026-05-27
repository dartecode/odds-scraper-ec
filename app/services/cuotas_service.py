from app.config.database import get_connection
import unicodedata
import re
from app.config.logger_config import configurar_logger

logger = configurar_logger("scraper_cuotas")

def normalizar_texto(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"[^a-z0-9 ]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def obtener_equipo_id_por_alias(cur, nombre_raw):
    alias = normalizar_texto(nombre_raw)

    cur.execute("""
        SELECT equipo_id
        FROM equipo_alias
        WHERE alias = %s
        LIMIT 1
    """, (alias,))

    row = cur.fetchone()

    if not row:
        raise Exception(f"No existe alias para equipo: {nombre_raw} -> {alias}")

    return row[0]


def obtener_o_crear_casa_apuesta(cur, nombre):
    cur.execute("""
        SELECT id
        FROM casa_apuesta
        WHERE nombre = %s
        LIMIT 1
    """, (nombre,))

    row = cur.fetchone()

    if row:
        return row[0]

    cur.execute("""
        INSERT INTO casa_apuesta (nombre, activo)
        VALUES (%s, true)
        RETURNING id
    """, (nombre,))

    return cur.fetchone()[0]


def obtener_o_crear_partido(cur, cuota):
    equipo_local_id = obtener_equipo_id_por_alias(cur, cuota.equipo_local)
    equipo_visitante_id = obtener_equipo_id_por_alias(cur, cuota.equipo_visitante)

    cur.execute("""
        SELECT id
        FROM partido
        WHERE equipo_local_id = %s
          AND equipo_visitante_id = %s
          AND fecha_partido = %s
        LIMIT 1
    """, (
        equipo_local_id,
        equipo_visitante_id,
        cuota.fecha_partido
    ))

    row = cur.fetchone()

    if row:
        return row[0]

    cur.execute("""
        INSERT INTO partido (
            equipo_local,
            equipo_visitante,
            equipo_local_id,
            equipo_visitante_id,
            fecha_partido
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        cuota.equipo_local,
        cuota.equipo_visitante,
        equipo_local_id,
        equipo_visitante_id,
        cuota.fecha_partido
    ))

    return cur.fetchone()[0]


def obtener_mercado_id(cur, mercado_codigo):
    cur.execute("""
        SELECT id
        FROM mercado
        WHERE codigo = %s
        LIMIT 1
    """, (mercado_codigo,))

    row = cur.fetchone()

    if not row:
        raise Exception(f"No existe mercado: {mercado_codigo}")

    return row[0]


def obtener_seleccion_id(cur, mercado_id, seleccion_codigo):
    cur.execute("""
        SELECT id
        FROM selecciones_mercado
        WHERE mercado_id = %s
          AND codigo = %s
        LIMIT 1
    """, (
        mercado_id,
        seleccion_codigo
    ))

    row = cur.fetchone()

    if not row:
        raise Exception(
            f"No existe selección {seleccion_codigo} "
            f"para mercado_id {mercado_id}"
        )

    return row[0]


def cuota_no_cambio(
    cur,
    partido_id,
    casa_apuesta_id,
    mercado_id,
    seleccion_id,
    linea,
    nueva_cuota
):
    cur.execute("""
        SELECT cuota
        FROM cuota
        WHERE partido_id = %s
          AND casa_apuesta_id = %s
          AND mercado_id = %s
          AND seleccion_id = %s
          AND (
                linea = %s
                OR (linea IS NULL AND %s IS NULL)
              )
        ORDER BY fecha_captura DESC
        LIMIT 1
    """, (
        partido_id,
        casa_apuesta_id,
        mercado_id,
        seleccion_id,
        linea,
        linea
    ))

    row = cur.fetchone()

    if not row:
        return False

    ultima_cuota = row[0]

    return str(ultima_cuota) == str(nueva_cuota)


def insertar_cuotas(cuotas):
    conn = get_connection()

    insertadas = 0
    ignoradas = 0

    try:
        with conn.cursor() as cur:
            total = len(cuotas)

            logger.info("Iniciando inserción...")
            logger.info("Total cuotas recibidas: %s", total)

            for i, cuota in enumerate(cuotas, start=1):
                logger.info(
                    f"Procesando {i}/{total} - "
                    f"{cuota.equipo_local} vs {cuota.equipo_visitante} - "
                    f"{cuota.mercado_codigo} - {cuota.seleccion} - "
                    f"{cuota.linea} - {cuota.cuota}"
                )

                casa_apuesta_id = obtener_o_crear_casa_apuesta(
                    cur,
                    cuota.casa_apuesta_nombre
                )

                partido_id = obtener_o_crear_partido(
                    cur,
                    cuota
                )

                mercado_id = obtener_mercado_id(
                    cur,
                    cuota.mercado_codigo
                )

                seleccion_id = obtener_seleccion_id(
                    cur,
                    mercado_id,
                    cuota.seleccion
                )

                if cuota_no_cambio(
                    cur,
                    partido_id,
                    casa_apuesta_id,
                    mercado_id,
                    seleccion_id,
                    cuota.linea,
                    cuota.cuota
                ):
                    ignoradas += 1
                    continue

                cur.execute("""
                    INSERT INTO cuota (
                        partido_id,
                        casa_apuesta_id,
                        mercado,
                        seleccion,
                        linea,
                        cuota,
                        fecha_captura,
                        fecha_mod,
                        mercado_id,
                        seleccion_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
                """, (
                    partido_id,
                    casa_apuesta_id,
                    cuota.mercado_codigo,
                    cuota.seleccion,
                    cuota.linea,
                    cuota.cuota,
                    cuota.fecha_captura,
                    mercado_id,
                    seleccion_id
                ))

                insertadas += 1

        conn.commit()

        logger.info("Inserción finalizada.")
        logger.info(f"Cuotas insertadas: {insertadas}")
        logger.info(f"Cuotas ignoradas sin cambio: {ignoradas}")

    except Exception as e:
        conn.rollback()
        logger.error("Error insertando cuotas:")
        logger.error(e)

    finally:
        conn.close()