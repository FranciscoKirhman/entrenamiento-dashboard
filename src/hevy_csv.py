#!/usr/bin/env python3
"""Importa sesiones desde la exportación CSV de Hevy, para los perfiles sin clave de API (sin Pro).

  python3 src/hevy_csv.py            # busca exportaciones y agrega lo nuevo
  python3 src/hevy_csv.py --dry-run  # muestra qué agregaría, sin escribir nada
  python3 src/hevy_csv.py archivo.csv [--dry-run]

En el teléfono: Perfil → Ajustes → Exportar e importar datos → Exportar entrenamientos. El archivo
(workout_data.csv) se manda al Mac por AirDrop, WhatsApp o correo y se deja en ~/Downloads o en
~/Documents/Entrenamiento/hevy_csv. No hay que renombrarlo.

El CSV no dice de quién es. El perfil se reconoce por las sesiones ya registradas: se cuentan las
sesiones del archivo (fecha + título) que ya están en cada registro y gana el que tenga al menos
tres coincidencias, si ningún otro tiene. Los perfiles con clave de API se saltan: esos entran
por hevy_sync.py.

La exportación trae el historial completo, así que se puede importar el mismo archivo muchas
veces: solo entra lo posterior a la última sesión registrada, con la misma regla de hevy_sync
(`<!-- hevy:csv-AAAAMMDDHHMM -->` hace de id, porque el CSV no trae uno).
"""
import csv, datetime as dt, glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hevy_sync as H

CARPETAS = [os.path.expanduser("~/Downloads"), os.path.join(H.DOCS, "hevy_csv")]
MESES = {"jan": 1, "ene": 1, "feb": 2, "mar": 3, "apr": 4, "abr": 4, "may": 5, "jun": 6, "jul": 7,
         "aug": 8, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dec": 12, "dic": 12}


def fecha(s):
    """'28 May 2026, 18:05', 'Sep 20, 2026 at 2:51 PM', '20 sept 2026, 14:51' o ISO → datetime local."""
    s = (s or "").strip()
    try:
        return dt.datetime.fromisoformat(s).replace(tzinfo=None)
    except ValueError:
        pass
    m = (re.search(r"(\d{1,2})\s+([A-Za-zé]{3,})\.?\s+(\d{4})", s)
         or re.search(r"([A-Za-zé]{3,})\.?\s+(\d{1,2}),?\s+(\d{4})", s))
    h = re.search(r"(\d{1,2}):(\d{2})\s*([ap]\.?\s*m\.?)?", s[m.end():] if m else "", re.I)
    if not m or not h:
        raise ValueError(f"fecha que no reconozco: {s!r}")
    a, b, anio = m.groups()
    dia, mes = (a, b) if a.isdigit() else (b, a)
    hora, minuto, ampm = int(h.group(1)), int(h.group(2)), (h.group(3) or "").lower()
    if ampm.startswith("p") and hora < 12:
        hora += 12
    if ampm.startswith("a") and hora == 12:
        hora = 0
    return dt.datetime(int(anio), MESES[mes[:3].lower()], int(dia), hora, minuto)


def num(x):
    x = (x or "").strip().replace(",", ".")
    return float(x) if x else None


def es_exportacion(ruta):
    try:
        with open(ruta, encoding="utf-8-sig") as f:
            cab = f.readline()
    except (OSError, UnicodeDecodeError):
        return False
    return "exercise_title" in cab and "start_time" in cab


def lee(ruta):
    """Filas del CSV → sesiones con la misma forma que entrega la API de Hevy."""
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))
    ses = {}
    for r in filas:
        ini = fecha(r["start_time"])
        w = ses.setdefault((ini, r.get("title", "").strip()), {
            "id": f"csv-{ini:%Y%m%d%H%M}", "title": r.get("title", "").strip() or "Entrenamiento",
            "start_time": ini.replace(tzinfo=H.TZ).isoformat(),
            "end_time": (fecha(r["end_time"]) if r.get("end_time") else ini).replace(tzinfo=H.TZ).isoformat(),
            "description": r.get("description") or "", "exercises": []})
        ej = r.get("exercise_title", "").strip()
        exs = w["exercises"]
        if not exs or exs[-1]["title"] != ej:        # el mismo ejercicio puede volver más tarde en la sesión
            exs.append({"title": ej, "index": len(exs), "notes": r.get("exercise_notes") or "", "sets": []})
        kg = num(r.get("weight_kg"))
        if kg is None and num(r.get("weight_lbs")) is not None:
            kg = num(r["weight_lbs"]) * 0.45359237
        km, reps, seg = num(r.get("distance_km")), num(r.get("reps")), num(r.get("duration_seconds"))
        exs[-1]["sets"].append({
            "index": int(num(r.get("set_index")) or len(exs[-1]["sets"])),
            "weight_kg": kg, "reps": int(reps) if reps is not None else None,
            "duration_seconds": int(seg) if seg else None,
            "distance_meters": km * 1000 if km else None, "rpe": num(r.get("rpe"))})
    return list(ses.values())


def de_quien(ws, textos):
    """Perfil cuyo registro ya tiene al menos tres de las sesiones del archivo; None si no hay uno claro."""
    claves = {(H.local(w["start_time"]).date(), w["title"].strip()) for w in ws}
    votos = {}
    for perfil, texto in textos.items():
        reg = {(d, b.split("\n", 1)[0].split(" — ", 1)[-1].strip()) for d, b in H.fechas_registradas(texto)}
        votos[perfil] = len(claves & reg)
    buenos = [p for p, v in votos.items() if v >= 3]
    return (buenos[0] if len(buenos) == 1 else None), votos


def filtra(ws, texto):
    """Misma regla que hevy_sync.nuevas, sobre una lista ya leída."""
    ses = H.fechas_registradas(texto)
    ultima = max(d for d, _ in ses) if ses else dt.date.min
    ultima_de_hevy = all("<!-- hevy:" in b for d, b in ses if d == ultima)
    vistos = set(re.findall(r"<!-- hevy:([\w-]+) -->", texto))
    ya = H.registradas(texto)                 # la misma sesión pudo entrar antes por la web de Hevy
    out = [w for w in ws if w["id"] not in vistos and H.clave_sesion(w) not in ya and not (
        H.local(w["start_time"]).date() < ultima
        or (H.local(w["start_time"]).date() == ultima and not ultima_de_hevy))]
    return sorted(out, key=lambda w: w["start_time"])


def sincroniza(dry=False, rutas=None):
    import parse_log
    rutas = rutas or sorted((r for c in CARPETAS for r in glob.glob(os.path.join(c, "*.csv")) if es_exportacion(r)),
                            key=os.path.getmtime)
    sin_clave = [p for p in H.REGISTROS if not H.clave(p)]
    if not rutas or not sin_clave:
        return []
    perfiles = json.load(open(H.PROFILES, encoding="utf-8"))
    agregadas = []
    for ruta in rutas:
        textos = {p: open(os.path.join(H.DOCS, H.REGISTROS[p]), encoding="utf-8").read() for p in H.REGISTROS}
        ws = lee(ruta)
        perfil, votos = de_quien(ws, textos)
        nombre = os.path.basename(ruta)
        if perfil is None:
            print(f"hevy csv {nombre}: no sé de quién es (coincidencias {votos}), no se importa")
            continue
        if perfil not in sin_clave:
            continue                                   # ese perfil entra por la API
        nuevas = filtra(ws, textos[perfil])
        if not nuevas:
            print(f"hevy csv {perfil} ({nombre}): sin sesiones nuevas")
            continue
        for w in nuevas:
            print(f"hevy csv {perfil}: {H.local(w['start_time']):%Y-%m-%d %H:%M} — {w['title']}")
        if dry:
            continue
        reg = os.path.join(H.DOCS, H.REGISTROS[perfil])
        texto = H.cabecera(textos[perfil].rstrip("\n") + "\n\n" + "\n".join(H.bloque(w) for w in nuevas))
        open(reg, "w", encoding="utf-8").write(texto)
        nuevas_json = parse_log.parse(reg)[-len(nuevas):]
        perfiles[perfil]["SESSIONS_FULL"] = nuevas_json[::-1] + perfiles[perfil]["SESSIONS_FULL"]
        agregadas.append(f"{perfil} +{len(nuevas)}")
    if agregadas:
        json.dump(perfiles, open(H.PROFILES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return agregadas


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    r = sincroniza(dry="--dry-run" in sys.argv, rutas=args or None)
    if r:
        print("agregadas:", ", ".join(r), "— publica con: python3 src/publish.py \"sesiones desde Hevy\"")
