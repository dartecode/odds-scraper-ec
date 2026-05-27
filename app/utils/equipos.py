import unicodedata
import re

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
        raise Exception(
            f"No existe alias para equipo: {nombre_raw} -> {alias}"
        )

    return row[0]