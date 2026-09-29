#!/usr/bin/env python3
"""Trae de la API de Hevy las sesiones nuevas y las agrega al registro markdown y a profiles.json.

  python3 src/hevy_sync.py            # sincroniza los perfiles que tengan clave
  python3 src/hevy_sync.py --dry-run  # muestra qué agregaría, sin escribir nada

La clave de cada perfil se lee de ~/.config/hevy/<perfil>.key (o de HEVY_API_KEY_<PERFIL>), nunca
del repo. Un perfil sin clave se salta en silencio.

Qué cuenta como nuevo: una sesión de Hevy cuyo id no esté ya en el registro y cuya fecha sea
posterior a la última sesión registrada. Si coincide con esa última fecha solo entra cuando las de
ese día también vinieron de Hevy (llevan `<!-- hevy:id -->`); así no se duplica una sesión que se
anotó a mano, como la del 20 sep de Mopo. Lo que entra se agrega al final del markdown (canónico) y
se antepone a SESSIONS_FULL usando parse_log, igual que se venía haciendo a mano.
"""
import datetime as dt, json, os, re, sys, urllib.error, urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.expanduser("~/Documents/Entrenamiento")
PROFILES = os.path.join(ROOT, "src", "profiles.json")
REGISTROS = {"mopo": "Registro_historico_consolidado.md", "mipi": "Registro_historico_Mipi.md"}
API = "https://api.hevyapp.com/v1/workouts"
TZ = ZoneInfo("America/Santiago")
MESES_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
            "septiembre", "octubre", "noviembre", "diciembre"]
MES_NUM = {m: i + 1 for i, m in enumerate(MESES_EN)} | {"Ene": 1, "Abr": 4, "Ago": 8, "Dic": 12}
CABEZA = re.compile(r"^## (\d{1,2}) (\w{3}) (\d{4}) — .+$", re.M)


def clave(perfil):
    k = os.environ.get(f"HEVY_API_KEY_{perfil.upper()}")
    f = os.path.expanduser(f"~/.config/hevy/{perfil}.key")
    if not k and os.path.exists(f):
        k = open(f).read()
    return (k or "").strip() or None


def pide(key, pagina):
    req = urllib.request.Request(f"{API}?page={pagina}&pageSize=10",
                                 headers={"api-key": key, "accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:          # página fuera de rango
            return {"workouts": [], "page_count": 0}
        if e.code in (401, 403):
            sys.exit(f"Hevy rechazó la clave ({e.code}). ¿Es de una cuenta Pro y está bien copiada?")
        raise


def local(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)


def num(x):
    s = f"{round(float(x), 2):.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def miles(x):
    return f"{int(x + 0.5):,}"   # medio hacia arriba, como Hevy (round() de Python redondea 3612,5 a 3612)


def fila(orden, ej, serie, s):
    kg, reps, seg, dist = s.get("weight_kg"), s.get("reps"), s.get("duration_seconds"), s.get("distance_meters")
    if reps is not None:
        carga, rt = (f"{num(kg)} kg" if kg else "Peso corporal"), str(reps)
    elif seg:
        carga, rt = (f"{num(kg)} kg" if kg else "Peso corporal (isométrico)"), f"{seg} s"
    elif dist:
        carga, rt = (f"{num(kg)} kg" if kg else "—"), f"{num(dist)} m"
    else:
        carga, rt = (f"{num(kg)} kg" if kg else "—"), "—"
    rpe = num(s["rpe"]) if s.get("rpe") is not None else "—"
    return f"| {orden} | {ej} | {serie} | {carga} | {rt} | {rpe} |"


def bloque(w):
    ini, fin = local(w["start_time"]), local(w["end_time"])
    mins = round((fin - ini).total_seconds() / 60)
    dur = f"{mins // 60}h {mins % 60}m" if mins >= 60 else f"{mins}m"
    vol = sum((s.get("weight_kg") or 0) * (s.get("reps") or 0)
              for e in w["exercises"] for s in e["sets"])
    hora = ini.strftime("%I:%M %p").lstrip("0")
    L = [f"## {ini.day} {MESES_EN[ini.month - 1]} {ini.year} — {w['title'].strip()}", "",
         f"<!-- hevy:{w['id']} -->", f"**Hora:** {hora}  ", f"**Duración:** {dur}  ",
         f"**Volumen Hevy:** {miles(vol)} kg  "]
    if (w.get("description") or "").strip():
        L.append(f"**Comentario:** {' '.join(w['description'].split())}  ")
    L += ["", "| Orden | Ejercicio | Serie | Carga | Reps/tiempo | RPE |", "|---:|---|---:|---:|---|---:|"]
    for i, e in enumerate(sorted(w["exercises"], key=lambda e: e.get("index", 0)), 1):
        for j, s in enumerate(sorted(e["sets"], key=lambda s: s.get("index", 0)), 1):
            L.append(fila(i, e["title"].strip(), j, s))
    notas = [(e["title"].strip(), " ".join(e["notes"].split()))
             for e in w["exercises"] if (e.get("notes") or "").strip()]
    if notas:
        L += ["", "**Notas por ejercicio:**"] + [f"- **{t}:** {n}" for t, n in notas]
    return "\n".join(L) + "\n"


def fechas_registradas(texto):
    """[(fecha, bloque)] de cada sesión del markdown."""
    heads = list(CABEZA.finditer(texto))
    return [(dt.date(int(m.group(3)), MES_NUM[m.group(2)], int(m.group(1))),
             texto[m.start(): heads[i + 1].start() if i + 1 < len(heads) else len(texto)])
            for i, m in enumerate(heads)]


def nuevas(key, texto):
    ses = fechas_registradas(texto)
    ultima = max(d for d, _ in ses) if ses else dt.date.min
    ultima_de_hevy = all("<!-- hevy:" in b for d, b in ses if d == ultima)
    vistos = set(re.findall(r"<!-- hevy:([\w-]+) -->", texto))
    out, pagina = [], 1
    while True:
        r = pide(key, pagina)
        ws = r.get("workouts") or []
        for w in ws:
            d = local(w["start_time"]).date()
            if w["id"] in vistos or d < ultima or (d == ultima and not ultima_de_hevy):
                continue
            out.append(w)
        # Hevy entrega de la más nueva a la más antigua: se corta al pasar la última fecha registrada
        if not ws or pagina >= r.get("page_count", pagina) or min(local(w["start_time"]).date() for w in ws) < ultima:
            break
        pagina += 1
    return sorted(out, key=lambda w: w["start_time"])


def cabecera(texto):
    """Pone al día el rango de fechas y el conteo del título '# Historial ... al X de mes de AAAA (N sesiones)'."""
    ses = fechas_registradas(texto)
    if not ses:
        return texto
    u = max(d for d, _ in ses)
    return re.sub(r"al \d{1,2} de \w+ de \d{4} \(\d+ sesiones\)",
                  f"al {u.day} de {MESES_ES[u.month - 1]} de {u.year} ({len(ses)} sesiones)", texto, count=1)


def sincroniza(dry=False):
    sys.path.insert(0, os.path.join(ROOT, "src"))
    import parse_log
    perfiles = json.load(open(PROFILES, encoding="utf-8"))
    agregadas = []
    for perfil, archivo in REGISTROS.items():
        key = clave(perfil)
        if not key:
            continue
        ruta = os.path.join(DOCS, archivo)
        texto = open(ruta, encoding="utf-8").read()
        ws = nuevas(key, texto)
        if not ws:
            print(f"hevy {perfil}: sin sesiones nuevas")
            continue
        for w in ws:
            print(f"hevy {perfil}: {local(w['start_time']):%Y-%m-%d %H:%M} — {w['title'].strip()}")
        if dry:
            continue
        texto = cabecera(texto.rstrip("\n") + "\n\n" + "\n".join(bloque(w) for w in ws))
        open(ruta, "w", encoding="utf-8").write(texto)
        # SESSIONS_FULL va de la más nueva a la más antigua: se anteponen las recién agregadas
        nuevas_json = parse_log.parse(ruta)[-len(ws):]
        perfiles[perfil]["SESSIONS_FULL"] = nuevas_json[::-1] + perfiles[perfil]["SESSIONS_FULL"]
        agregadas.append(f"{perfil} +{len(ws)}")
    if agregadas:
        json.dump(perfiles, open(PROFILES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return agregadas


if __name__ == "__main__":
    r = sincroniza(dry="--dry-run" in sys.argv)
    if r:
        print("agregadas:", ", ".join(r), "— publica con: python3 src/publish.py \"sesiones desde Hevy\"")
