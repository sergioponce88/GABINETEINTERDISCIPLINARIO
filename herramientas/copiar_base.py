"""Copia COMPLETA de una base de Supabase a otra (todas las tablas del esquema public: estructura + datos).

- La base vieja NO se modifica (se abre en modo solo lectura).
- En la nueva crea secuencias, tablas, claves, índices y restricciones iguales a las de la vieja,
  copia los datos, ajusta las numeraciones y compara la cantidad de filas de cada tabla.
- Sirve para cualquiera de los sistemas (Gabinete, Legajos, etc.): no depende del código de la app.

Uso (en la PC):
    pip install psycopg2-binary
    python herramientas/copiar_base.py

Pide las dos direcciones (Supabase → Connect → Session pooler, puerto 5432).
"""
import io
import os
import sys

import psycopg2


def _limpiar(txt):
    """Se queda solo con la dirección (descarta «VIEJA:», «SUPABASE_DB_URL =», comillas y espacios)."""
    txt = (txt or "").strip()
    for inicio in ("postgresql://", "postgres://"):
        if inicio in txt:
            txt = txt[txt.index(inicio):]
            break
    return txt.split()[0].strip("\"'") if txt else ""


def _pedir(texto):
    """Pide una dirección; si llega vacía (Enter de más al pegar) la vuelve a pedir."""
    while True:
        url = _limpiar(input(texto))
        if url:
            print(f"   ✔ recibida: {_oculta(url)}\n")
            return url


def _oculta(url):
    if "://" in url and "@" in url:
        pre, resto = url.split("://", 1)
        cred, host = resto.rsplit("@", 1)
        return f"{pre}://{cred.split(':', 1)[0]}:****@{host}"
    return (url[:25] + "…") if len(url) > 25 else (url or "(vacía)")


def q(cur, sql, params=None):
    cur.execute(sql, params)
    return cur.fetchall()


def ident(nombre):
    return '"' + nombre.replace('"', '""') + '"'


# ───────────────────────── Lectura de la estructura (base vieja) ─────────────────────────
def tablas(cur):
    return [r[0] for r in q(cur, "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                                 "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') ORDER BY c.relname")]


def secuencias(cur):
    return q(cur, "SELECT s.relname, format_type(q.seqtypid, NULL), q.seqstart, q.seqincrement, q.seqmin, q.seqmax, "
                  "q.seqcycle FROM pg_sequence q JOIN pg_class s ON s.oid = q.seqrelid "
                  "JOIN pg_namespace n ON n.oid = s.relnamespace WHERE n.nspname = 'public' "
                  "AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = s.oid AND d.deptype = 'i')")  # no identity


def duenios_secuencias(cur):
    """[(secuencia, tabla, columna)] de las columnas SERIAL: para que la secuencia quede atada a su columna."""
    return q(cur, """
        SELECT s.relname, t.relname, a.attname FROM pg_depend d
        JOIN pg_class s ON s.oid = d.objid AND s.relkind = 'S'
        JOIN pg_class t ON t.oid = d.refobjid
        JOIN pg_namespace n ON n.oid = t.relnamespace AND n.nspname = 'public'
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
        WHERE d.deptype = 'a'""")


def ddl_tabla(cur, t):
    cols = q(cur, """
        SELECT a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull, pg_get_expr(d.adbin, d.adrelid),
               a.attidentity, a.attgenerated
        FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum""",
             (f"public.{ident(t)}",))
    partes = []
    for nom, tipo, nn, defecto, identidad, generada in cols:
        p = f"{ident(nom)} {tipo}"
        if generada == "s":
            p += f" GENERATED ALWAYS AS ({defecto}) STORED"
        elif identidad:
            p += " GENERATED " + ("ALWAYS" if identidad == "a" else "BY DEFAULT") + " AS IDENTITY"
        elif defecto is not None:
            p += f" DEFAULT {defecto}"
        if nn:
            p += " NOT NULL"
        partes.append(p)
    return f"CREATE TABLE IF NOT EXISTS public.{ident(t)} (\n  " + ",\n  ".join(partes) + "\n)"


def restricciones(cur, t, tipos):
    return q(cur, "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                  "WHERE conrelid = %s::regclass AND contype = ANY(%s) ORDER BY contype, conname",
             (f"public.{ident(t)}", list(tipos)))


def indices(cur, t):
    return [r[0] for r in q(cur, """
        SELECT pg_get_indexdef(i.indexrelid) FROM pg_index i
        WHERE i.indrelid = %s::regclass
          AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = i.indexrelid)""", (f"public.{ident(t)}",))]


def columnas_copiables(cur, t):
    return [r[0] for r in q(cur, "SELECT a.attname FROM pg_attribute a WHERE a.attrelid = %s::regclass "
                                 "AND a.attnum > 0 AND NOT a.attisdropped AND a.attgenerated = '' ORDER BY a.attnum",
                            (f"public.{ident(t)}",))]


def contar(cur, t):
    cur.execute(f"SELECT COUNT(*) FROM public.{ident(t)}")
    return cur.fetchone()[0]


# ───────────────────────── Copia ─────────────────────────
def main():
    print("=== Copia completa de base Supabase (estructura + datos) ===\n")
    print("Pegue cada dirección con clic derecho (o Ctrl+V) y apriete Enter.\n")
    origen = _pedir("Dirección de la base VIEJA: ")
    destino = _pedir("Dirección de la base NUEVA: ")
    os.system("cls" if os.name == "nt" else "clear")
    print("=== Copia completa de base Supabase (estructura + datos) ===\n")
    for nombre, url in (("VIEJA", origen), ("NUEVA", destino)):
        if not url.startswith(("postgresql://", "postgres://")) or "[" in url:
            sys.exit(f"❌ La dirección {nombre} no es válida (debe empezar con postgresql:// y no tener "
                     f"[YOUR-PASSWORD]).\n   Se recibió: {_oculta(url)}")
        print(f"  {nombre}: {_oculta(url)}")
    if origen == destino:
        sys.exit("❌ Las dos direcciones son iguales.")

    co = psycopg2.connect(origen, connect_timeout=15)
    co.set_session(readonly=True)
    cd = psycopg2.connect(destino, connect_timeout=15)
    o, d = co.cursor(), cd.cursor()
    print("✔ Conectado a las dos bases.")

    lista = tablas(o)
    if not lista:
        sys.exit("❌ La base vieja no tiene tablas. ¿Es la dirección correcta?")
    print(f"✔ La base vieja tiene {len(lista)} tablas: {', '.join(lista)}\n")

    ya = [t for t in tablas(d) if t in lista and contar(d, t)]
    if ya:
        print(f"⚠ La base nueva ya tiene datos en: {', '.join(ya)}")
        if input("¿Borrarlos y reemplazarlos por los de la base vieja? (escriba SI): ").strip().upper() != "SI":
            sys.exit("Cancelado. No se copió nada.")

    try:
        # 1) Secuencias sueltas (las de SERIAL), 2) tablas, 3) claves primarias y únicas
        for nom, tipo, ini, inc, mn, mx, ciclo in secuencias(o):
            d.execute(f"CREATE SEQUENCE IF NOT EXISTS public.{ident(nom)} AS {tipo} START {ini} INCREMENT {inc} "
                      f"MINVALUE {mn} MAXVALUE {mx} {'CYCLE' if ciclo else 'NO CYCLE'}")
        for t in lista:
            d.execute(ddl_tabla(o, t))
        for sec, t, col in duenios_secuencias(o):
            d.execute(f"ALTER SEQUENCE public.{ident(sec)} OWNED BY public.{ident(t)}.{ident(col)}")
        existentes = {r[0] for r in q(d, "SELECT conname FROM pg_constraint c JOIN pg_namespace n "
                                         "ON n.oid = c.connamespace WHERE n.nspname = 'public'")}
        for t in lista:
            for nom, defin in restricciones(o, t, "pu"):
                if nom not in existentes:
                    d.execute(f"ALTER TABLE public.{ident(t)} ADD CONSTRAINT {ident(nom)} {defin}")
                    existentes.add(nom)
        if ya:
            d.execute("TRUNCATE " + ", ".join(f"public.{ident(t)}" for t in lista) + " CASCADE")
        print("✔ Estructura creada en la base nueva.")

        # 4) Datos (todavía sin claves foráneas, así el orden no importa)
        for t in lista:
            cols_d = set(columnas_copiables(d, t))
            cols = [c for c in columnas_copiables(o, t) if c in cols_d]
            lc = ", ".join(ident(c) for c in cols)
            buf = io.StringIO()
            o.copy_expert(f"COPY (SELECT {lc} FROM public.{ident(t)}) TO STDOUT WITH (FORMAT csv)", buf)
            buf.seek(0)
            d.copy_expert(f"COPY public.{ident(t)} ({lc}) FROM STDIN WITH (FORMAT csv)", buf)
            print(f"  · {t}: copiada")

        # 5) Claves foráneas, controles e índices
        for t in lista:
            for nom, defin in restricciones(o, t, "fc"):
                if nom not in existentes:
                    d.execute(f"ALTER TABLE public.{ident(t)} ADD CONSTRAINT {ident(nom)} {defin}")
                    existentes.add(nom)
            for idx in indices(o, t):
                d.execute(idx.replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ", 1)
                          .replace("CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ", 1))

        # 6) Numeraciones: cada secuencia sigue desde el máximo valor copiado
        for t in lista:
            for (col,) in q(d, "SELECT a.attname FROM pg_attribute a WHERE a.attrelid = %s::regclass AND a.attnum > 0 "
                               "AND NOT a.attisdropped AND pg_get_serial_sequence(%s, a.attname) IS NOT NULL",
                            (f"public.{ident(t)}", f"public.{ident(t)}")):
                d.execute(f"SELECT setval(pg_get_serial_sequence(%s, %s), COALESCE(MAX({ident(col)})::bigint, 1), "
                          f"MAX({ident(col)}) IS NOT NULL) FROM public.{ident(t)}", (f"public.{ident(t)}", col))
        cd.commit()
    except Exception as e:
        cd.rollback()
        sys.exit(f"\n❌ Error al copiar: {e}\nSe deshizo todo en la base nueva; la vieja no se tocó.")

    print("\nControl de filas (vieja → nueva):")
    ok = True
    for t in lista:
        a, b = contar(o, t), contar(d, t)
        ok &= a == b
        print(f"  {'✔' if a == b else '✖'} {t:<24} {a:>7} → {b:>7}")
    co.close()
    cd.close()
    print("\n✅ Copia completa y verificada." if ok else "\n❌ Hay diferencias: no cambie todavía el Secret de la app.")


if __name__ == "__main__":
    main()
