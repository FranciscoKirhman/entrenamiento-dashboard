#!/usr/bin/env python3
"""Recalcula los números de los gráficos desde el historial (SESSIONS_FULL) de profiles.json.

  python3 src/graficos.py

Actualiza, para cada perfil:
  - CHARTS[].data: un punto por sesión con la carga tope del día en ese ejercicio.
  - MUSCLES[]: recent, trend, hist y tier.
Los textos (note, change, rationale) y las bandas (lo, hi) son criterio, no cálculo: no se tocan.

Reproduce lo que se venía calculando a mano: los 18 gráficos de carga coinciden punto por punto
con los que había, y el volumen reciente por músculo de Mopo coincide en los diez músculos.
"""
import datetime as dt, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "src", "profiles.json")
DIAS = 12   # ventana del volumen reciente

# ---------------------------------------------------------------- carga tope por sesión
EQUIPO = {"barbell", "dumbbell", "cable", "machine", "smith", "spa", "unilateral"}


def _norm(n):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", (n or "").lower()).split())


def _kg(v):
    m = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s*(?:kg)?\s*$", str(v or ""))
    return float(m.group(1).replace(",", ".")) if m else None


def coincide(grafico, ejercicio):
    """'Bench Press (Barbell)' toma 'Bench Press — Barbell'; 'Lat Pulldown' toma cualquier equipo,
    pero no 'Lat Pulldown - Close Grip', que es otro ejercicio."""
    k, e = _norm(grafico), _norm(ejercicio)
    if e == k:
        return True
    return e.startswith(k + " ") and set(e[len(k):].split()) <= EQUIPO and not set(k.split()) & EQUIPO


def puntos(sesiones, grafico):
    out = []
    for s in sorted(sesiones, key=lambda s: s["date"]):
        cargas = [_kg(e["carga"]) for e in s["exercises"] if coincide(grafico, e["ej"])]
        cargas = [c for c in cargas if c]
        if cargas:
            out.append({"d": s["dlabel"], "w": max(cargas)})
    return out


# ---------------------------------------------------------------- series por músculo
MAPA = {
    "Femoral":            ["romanian deadlift", "leg curl", "good morning"],
    "Glúteo / cadera":    ["hip thrust", "back extension", "glute kickback"],
    "Cuádriceps":         ["squat", "leg press", "leg extension", "step up"],
    "Aductor / abductor": ["hip adduction", "hip abduction", "abductor"],
    "Espalda":            ["lat pulldown", "seated row", "pull up", "chin up", "iso-lateral row", "bent over row",
                           "landmine row", "dumbbell row", "cable row"],
    "Pecho":              ["bench press", "chest fly", "chest press", "cable fly", "chest dip", "butterfly"],
    "Hombro":             ["shoulder press", "overhead press", "lateral raise", "rear delt", "face pull",
                           "front raise", "reverse fly"],
    "Bíceps":             ["bicep curl", "preacher curl", "hammer curl", "incline curl", "behind the back curl",
                           "behind-the-back curl"],
    "Tríceps":            ["triceps", "skullcrusher"],
    "Core":               ["crunch", "plank", "plancha", "pallof", "dead bug", "heel taps", "knee raise", "leg raise",
                           "hollow", "v up", "russian twist", "jackknife", "around the world", "bird dog",
                           "cable twist", "marcha"],
}


def musculo(nombre):
    """En Mopo la fila se llama 'Hombro (empuje)'."""
    return "Hombro" if nombre.startswith("Hombro") else nombre


def efectiva(e):
    """Las series a RPE 6 o menos son de aproximación. Sin RPE, cuenta si es de peso corporal."""
    try:
        return float(e["rpe"].replace(",", ".")) > 6
    except ValueError:
        return e["carga"].startswith("Peso corporal")


def series(sesiones, ini, fin):
    c = dict.fromkeys(MAPA, 0)
    for s in sesiones:
        if ini <= dt.date.fromisoformat(s["date"]) <= fin:
            for e in s["exercises"]:
                if not efectiva(e):
                    continue
                n = e["ej"].lower()
                for m, claves in MAPA.items():
                    if any(k in n for k in claves) and "puente" not in n:
                        c[m] += 1
    return c


def volumen(sesiones):
    """Series efectivas por semana: las últimas 12 días hasta la última sesión, la ventana anterior
    y el promedio de todo el historial."""
    fechas = [dt.date.fromisoformat(s["date"]) for s in sesiones]
    fin, primera = max(fechas), min(fechas)
    ini = fin - dt.timedelta(days=DIAS - 1)
    rec = series(sesiones, ini, fin)
    ant = series(sesiones, ini - dt.timedelta(days=DIAS), ini - dt.timedelta(days=1))
    tot = series(sesiones, primera, fin)
    semanas = ((fin - primera).days + 1) / 7
    return {m: {"recent": round(rec[m] * 7 / DIAS, 1),
                "trend": round((rec[m] - ant[m]) * 7 / DIAS, 1),
                "hist": round(tot[m] / semanas, 1)} for m in MAPA}


def tier(recent, lo):
    return "good" if recent >= lo else ("critical" if recent < lo / 2 else "warning")


# ---------------------------------------------------------------- aplicar
def actualiza(profiles):
    """Devuelve la lista de cambios; modifica profiles en el lugar."""
    cambios = []
    for perfil, datos in profiles.items():
        ses = datos.get("SESSIONS_FULL") or []
        if not ses:
            continue
        for g in datos.get("CHARTS", []):
            nuevos = puntos(ses, g["name"])
            if nuevos and nuevos != g["data"]:
                cambios.append(f"{perfil} gráfico {g['name']}: {len(g['data'])} → {len(nuevos)} puntos")
                g["data"] = nuevos
        vol = volumen(ses)
        for m in datos.get("MUSCLES", []):
            v = dict(vol[musculo(m["name"])], tier=tier(vol[musculo(m["name"])]["recent"], m["lo"]))
            viejo = {k: m.get(k) for k in v}
            if viejo != v:
                cambios.append(f"{perfil} {m['name']}: {viejo['recent']} → {v['recent']} series/sem ({v['tier']})")
                m.update(v)
    return cambios


if __name__ == "__main__":
    profiles = json.load(open(PATH, encoding="utf-8"))
    cambios = actualiza(profiles)
    json.dump(profiles, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(cambios) if cambios else "gráficos al día")
