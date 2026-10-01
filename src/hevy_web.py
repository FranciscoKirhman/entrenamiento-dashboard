#!/usr/bin/env python3
"""Registra sesiones leídas de la web de Hevy (hevy.com), para quien no tiene Pro ni quiere exportar.

  python3 src/hevy_web.py mipi sesion1.txt [sesion2.txt ...]            # agrega lo nuevo
  python3 src/hevy_web.py mipi sesion1.txt --dry-run                    # muestra qué agregaría
  python3 src/hevy_web.py mipi --ultima                                 # última sesión registrada

Cada archivo es el texto de la página de un entrenamiento (https://hevy.com/workout/<id>), tal como
lo devuelve get_page_text de Claude in Chrome, con la línea "URL: ..." incluida. Lo usa el agente que
revisa el Hevy de Mipi en Chrome: abre cada entrenamiento nuevo, guarda su texto y corre esto.

Fechas: Hevy muestra "Sep 27, 2026, 12:53 PM", pero para lo reciente usa "Today at 6:02 PM",
"Yesterday at 6:02 PM", el día de la semana ("Monday at …") o "3 hours ago". Esas se resuelven contra el
momento en que se guardó el archivo (su fecha de modificación), que es cuando se leyó la página.

Qué valida antes de registrar: que el volumen calculado con lo leído (peso × reps + peso × metros,
calentamiento incluido, como lo cuenta Hevy) calce con el volumen oficial que muestra la página. Si no
calza, la sesión no entra: probablemente la página cambió de formato y hay que revisar el parser.

No duplica: una sesión con la misma fecha, hora y título que otra ya registrada (por la exportación
CSV, por ejemplo) se salta. El bloque que se escribe es igual al de hevy_sync, con
`<!-- hevy:web-<id> -->` y el volumen oficial de la página.
"""
import datetime as dt, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hevy_sync as H

MESES = {m: i + 1 for i, m in enumerate(H.MESES_EN)}
FECHA = re.compile(r"^([A-Z][a-z]{2}) (\d{1,2})(?:, (\d{4}))?(?:,| at) (\d{1,2}):(\d{2}) ([AP]M)$")
RELATIVA = re.compile(r"^(Today|Yesterday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) at (\d{1,2}):(\d{2}) ([AP]M)$")
HACE = re.compile(r"^(\d+|an?) (minute|hour)s? ago$|^just now$", re.I)
DIAS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MARCA = re.compile(r"^(W|D|F|\d+)$")
VALOR = re.compile(r"\d.*(kg|lbs|reps?|km|mi|\d\s*m\b|\d\s*s\b|\d\s*h\b)", re.I)
RPE = re.compile(r"^@\s*([\d.]+)\s*rpe$", re.I)
TIPOS = {"WEIGHT", "REPS", "DISTANCE", "TIME", "DURATION"}


def segundos(t):
    """'12m 0s', '40s', '1h 5m', '1:30' → segundos."""
    if (m := re.fullmatch(r"(\d+):(\d{2})", t.strip())):
        return int(m.group(1)) * 60 + int(m.group(2))
    total, hubo = 0, False
    for n, u in re.findall(r"(\d+)\s*([hms])\b", t):
        total += int(n) * {"h": 3600, "m": 60, "s": 1}[u]
        hubo = True
    return total if hubo else None


def serie(valor, tipo):
    """'20kg x 12 reps', '20kg - 30m', '0.8km - 12m 0s', '12 reps', '40s' → campos de una serie."""
    s = {"weight_kg": None, "reps": None, "duration_seconds": None, "distance_meters": None}
    partes = [p.strip() for p in re.split(r"\s+[x×-]\s+", valor)]
    campos = [c for c in re.split(r"\s*&\s*", tipo.upper()) if c in TIPOS]
    for i, p in enumerate(partes):
        campo = campos[i] if len(campos) == len(partes) else ""
        if (m := re.fullmatch(r"([+-]?[\d.]+)\s*(kg|lbs)", p, re.I)):
            kg = float(m.group(1)) * (0.45359237 if m.group(2).lower() == "lbs" else 1)
            s["weight_kg"] = kg
        elif (m := re.fullmatch(r"(\d+)\s*reps?", p, re.I)):
            s["reps"] = int(m.group(1))
        elif campo == "DISTANCE" or re.fullmatch(r"[\d.]+\s*(km|mi)", p, re.I):
            m = re.fullmatch(r"([\d.]+)\s*(km|mi|m)", p, re.I)
            if not m:
                raise ValueError(f"distancia que no reconozco: {p!r}")
            s["distance_meters"] = float(m.group(1)) * {"km": 1000, "mi": 1609.344, "m": 1}[m.group(2).lower()]
        elif (seg := segundos(p)) is not None:
            s["duration_seconds"] = seg
        else:
            raise ValueError(f"serie que no reconozco: {valor!r}")
    return s


def fecha_de(linea, ahora):
    """Línea de fecha de Hevy → datetime local; None si la línea no es una fecha."""
    if (m := FECHA.match(linea)):
        mes, dia, anio, hh, mm, ampm = m.groups()
        dia_ = dt.date(int(anio or ahora.year), MESES[mes], int(dia))
        if not anio and dia_ > ahora.date():          # sin año y "en el futuro": era el año pasado
            dia_ = dia_.replace(year=dia_.year - 1)
    elif (m := RELATIVA.match(linea)):
        cual, hh, mm, ampm = m.groups()
        if cual == "Today":
            dia_ = ahora.date()
        elif cual == "Yesterday":
            dia_ = ahora.date() - dt.timedelta(days=1)
        else:                                          # el último día con ese nombre, sin contar hoy
            atras = (ahora.weekday() - DIAS_EN.index(cual)) % 7 or 7
            dia_ = ahora.date() - dt.timedelta(days=atras)
    elif (m := HACE.match(linea)):
        if linea.lower() == "just now":
            return ahora.replace(second=0, microsecond=0)
        n = 1 if m.group(1).lower() in ("a", "an") else int(m.group(1))
        return (ahora - dt.timedelta(**{m.group(2).lower() + "s": n})).replace(second=0, microsecond=0)
    else:
        return None
    hora = int(hh) % 12 + (12 if ampm == "PM" else 0)
    return dt.datetime(dia_.year, dia_.month, dia_.day, hora, int(mm), tzinfo=H.TZ)


def lee_texto(texto, ahora=None):
    """Texto de la página de un entrenamiento → sesión con la forma de la API de Hevy + volumen oficial."""
    url = re.search(r"hevy\.com/workout/([\w-]+)", texto)
    if not url:
        raise ValueError("falta la línea URL: https://hevy.com/workout/<id>")
    L = [l.strip() for l in texto.splitlines() if l.strip()]
    ahora = ahora or dt.datetime.now(H.TZ)
    i = next((k for k, l in enumerate(L) if fecha_de(l, ahora)), None)
    if i is None:
        raise ValueError("no encuentro la fecha del entrenamiento")
    ini = fecha_de(L[i], ahora)
    titulo = L[i + 1]
    k = L.index("Duration", i)
    descripcion = " ".join(L[i + 2:k])
    dur = segundos(L[k + 1]) or 0
    kv = L.index("Volume", k)
    volumen = L[kv + 1]
    j = kv + 2
    while j < len(L) and L[j].isdigit():          # me gusta y comentarios
        j += 1
    ejercicios = []
    while j < len(L):
        try:
            s = L.index("SETS", j)
        except ValueError:
            break
        cab = [c for c in L[j:s] if not re.fullmatch(r"superset( \d+)?", c, re.I)]
        if not cab:
            raise ValueError(f"ejercicio sin nombre antes de la línea {s}")
        tipo, j, sets = L[s + 1], s + 2, []
        while j + 1 < len(L) and MARCA.match(L[j]) and VALOR.search(L[j + 1]):
            st = serie(L[j + 1], tipo)
            j += 2
            st["rpe"] = None
            if j < len(L) and (m := RPE.match(L[j])):
                st["rpe"] = float(m.group(1))
                j += 1
            st["index"] = len(sets)
            sets.append(st)
        ejercicios.append({"title": cab[0], "notes": " ".join(cab[1:]), "index": len(ejercicios), "sets": sets})
    if not ejercicios:
        raise ValueError("no encontré ejercicios")
    return {"id": "web-" + url.group(1), "title": titulo, "description": descripcion,
            "start_time": ini.isoformat(), "end_time": (ini + dt.timedelta(seconds=dur)).isoformat(),
            "exercises": ejercicios, "volumen_oficial": volumen}


def volumen(w):
    return sum((s["weight_kg"] or 0) * ((s["reps"] or 0) + (s["distance_meters"] or 0))
               for e in w["exercises"] for s in e["sets"] if (s["weight_kg"] or 0) > 0)


registradas, clave = H.registradas, H.clave_sesion


def bloque(w):
    b = H.bloque(w)
    return re.sub(r"\*\*Volumen Hevy:\*\* [^\n]*", f"**Volumen Hevy:** {w['volumen_oficial']}  ", b, count=1)


def agrega(perfil, rutas, dry=False):
    import parse_log
    reg = os.path.join(H.DOCS, H.REGISTROS[perfil])
    texto = open(reg, encoding="utf-8").read()
    ya, vistos = registradas(texto), set(re.findall(r"<!-- hevy:([\w-]+) -->", texto))
    nuevas = []
    for ruta in rutas:
        leido = dt.datetime.fromtimestamp(os.path.getmtime(ruta), H.TZ)   # cuando se guardó la página
        w = lee_texto(open(ruta, encoding="utf-8").read(), leido)
        nombre = f"{H.local(w['start_time']):%Y-%m-%d %H:%M} — {w['title']}"
        oficial = float(re.sub(r"[^\d.]", "", w["volumen_oficial"].replace(",", "")) or 0)
        calc = volumen(w)
        if abs(calc - oficial) > max(2, oficial * 0.01):
            print(f"hevy web {perfil}: {nombre}: el volumen leído ({calc:,.0f} kg) no calza con el de Hevy "
                  f"({w['volumen_oficial']}); no se registra")
            continue
        if w["id"] in vistos or clave(w) in ya or any(clave(w) == clave(x) for x in nuevas):
            print(f"hevy web {perfil}: {nombre}: ya estaba registrada")
            continue
        print(f"hevy web {perfil}: {nombre}: nueva ({len(w['exercises'])} ejercicios, {w['volumen_oficial']})")
        nuevas.append(w)
    if dry or not nuevas:
        return nuevas
    nuevas.sort(key=lambda w: w["start_time"])
    texto = H.cabecera(texto.rstrip("\n") + "\n\n" + "\n".join(bloque(w) for w in nuevas))
    open(reg, "w", encoding="utf-8").write(texto)
    perfiles = json.load(open(H.PROFILES, encoding="utf-8"))
    previas = perfiles[perfil]["SESSIONS_FULL"]
    hay = {(x.get("date"), x.get("hora"), x.get("title")) for x in previas}
    nuevas_json = [x for x in parse_log.parse(reg)[-len(nuevas):] if (x.get("date"), x.get("hora"), x.get("title")) not in hay]
    perfiles[perfil]["SESSIONS_FULL"] = nuevas_json[::-1] + previas
    json.dump(perfiles, open(H.PROFILES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return nuevas


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or args[0] not in H.REGISTROS:
        sys.exit(__doc__)
    perfil, rutas = args[0], args[1:]
    if "--ultima" in sys.argv:
        ses = H.fechas_registradas(open(os.path.join(H.DOCS, H.REGISTROS[perfil]), encoding="utf-8").read())
        print(max(d for d, _ in ses) if ses else "sin sesiones")
        sys.exit(0)
    n = agrega(perfil, rutas, dry="--dry-run" in sys.argv)
    if n and "--dry-run" not in sys.argv:
        print(f"agregadas: {perfil} +{len(n)} — publica con: python3 src/publish.py \"sesiones de {perfil} desde Hevy\"")
