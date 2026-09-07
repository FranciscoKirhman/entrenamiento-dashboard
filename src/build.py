#!/usr/bin/env python3
"""Reconstruye index.html desde src/. Ejecutar desde la raiz del repo:  python3 src/build.py"""
import hashlib, json, os, re, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "src")

FONTS = {"OSWALD_600":"oswald-600","OSWALD_700":"oswald-700",
         "PLEXSANS_400":"plexsans-400","PLEXSANS_500":"plexsans-500","PLEXSANS_600":"plexsans-600",
         "PLEXMONO_400":"plexmono-400","PLEXMONO_500":"plexmono-500"}

def _norm(n):
    """Nombre de ejercicio comparable entre el plan y el registro."""
    n = re.sub(r"\(.*?\)", " ", (n or "").lower())
    n = re.sub(r"[^a-z0-9áéíóúñü ]", " ", n)
    return " ".join(n.split())


def _kg(v):
    m = re.match(r"^\s*([\d]+(?:[.,][\d]+)?)\s*kg", str(v or ""), re.I)
    return float(m.group(1).replace(",", ".")) if m else None


def verifica_cargas(profiles, tope=1.10):
    """Ninguna carga prescrita puede pasarse del maximo ya levantado por mas de un 10%.

    Nace de un error real: a la elevacion lateral en polea, que iba en 7,5 kg, se le
    aplico una correccion pensada para la version con mancuernas y quedo prescrita en
    20 kg -- un 167% mas. El texto ademas decia 'baja de 24 a 20', asi que parecia
    una reduccion. Un salto asi tiene que romper el build, no llegar al gimnasio.
    Para un salto deliberado, poner "saltoOk": true en el ejercicio.
    """
    fallas = []
    for perfil, datos in profiles.items():
        techo = {}
        for ses in datos.get("SESSIONS_FULL", []):
            for e in ses.get("exercises", []):
                k = _norm(e.get("ej"))
                v = _kg(str(e.get("carga", "")) + " kg")
                if k and v:
                    techo[k] = max(techo.get(k, 0), v)
        for dia in datos.get("WEEKDAYS", []):
            for ex in (dia.get("exercises") or []):
                if ex.get("saltoOk"):
                    continue
                k = _norm(ex.get("name"))
                if k not in techo:
                    continue                      # sin historial: no hay contra que comparar
                for st in ex.get("sets", []):
                    v = _kg(st.get("carga"))
                    if v and v > techo[k] * tope:
                        fallas.append(
                            f"{perfil} {dia['date']} {ex['name']}: prescribe {v:g} kg y el maximo "
                            f"que ha levantado es {techo[k]:g} kg (+{(v/techo[k]-1)*100:.0f}%)")
                        break
    if fallas:
        raise SystemExit("cargas fuera de rango:\n  " + "\n  ".join(fallas))


def verifica_calentamientos(profiles):
    """Todo dia con ejercicios lleva calentamiento y estiramiento, con explicacion.

    Se paso una vez (el tren superior de Mipi del 28 de agosto salio sin ninguno de los
    dos) y ella lo noto. El build falla antes que volver a publicarlo asi.
    """
    fallas = []
    for perfil, datos in profiles.items():
        for dia in datos.get("WEEKDAYS", []):
            if not dia.get("exercises"):
                continue
            cal, est = dia.get("warmup") or [], dia.get("stretch") or []
            if len(cal) < 3:
                fallas.append(f"{perfil} {dia['date']}: {len(cal)} ejercicios de calentamiento (minimo 3)")
            if len(est) < 3:
                fallas.append(f"{perfil} {dia['date']}: {len(est)} estiramientos (minimo 3)")
            for bloque, nombre in ((cal, "calentamiento"), (est, "estiramiento")):
                for x in bloque:
                    if not (x.get("how") or "").strip():
                        fallas.append(f"{perfil} {dia['date']}: '{x.get('name')}' ({nombre}) sin explicacion")
    if fallas:
        raise SystemExit("calentamientos incompletos:\n  " + "\n  ".join(fallas))


def build():
    tpl = open(os.path.join(SRC,"dashboard.template.html"), encoding="utf-8").read()
    for key, slug in FONTS.items():
        b64 = open(os.path.join(SRC,"fonts",slug+".b64"), encoding="utf-8").read().strip()
        tpl = tpl.replace("{{"+key+"}}", b64)
    profiles = json.load(open(os.path.join(SRC,"profiles.json"), encoding="utf-8"))
    verifica_calentamientos(profiles)
    verifica_cargas(profiles)
    tpl = tpl.replace("__PROFILES_JSON__", json.dumps(profiles, ensure_ascii=False))
    cuerpos = json.load(open(os.path.join(SRC,"bodypaths.json"), encoding="utf-8"))
    tpl = tpl.replace("__BODYPATHS_JSON__", json.dumps(cuerpos, ensure_ascii=False, separators=(",",":")))
    assert "{{" not in tpl and "__PROFILES_JSON__" not in tpl and "__BODYPATHS_JSON__" not in tpl, "quedaron placeholders sin reemplazar"
    assert "__VERSION__" in tpl, "falta el marcador de version"
    assert 'name="viewport"' in tpl, "falta el meta viewport (rompe la vista movil)"
    version = hashlib.sha256(tpl.encode("utf-8")).hexdigest()[:12]
    tpl = tpl.replace("__VERSION__", version)
    out = os.path.join(ROOT,"index.html")
    open(out,"w",encoding="utf-8").write(tpl)
    # el tablero compara su propia version contra esta al abrirse; si no calzan, recarga solo.
    # Sin esto, una app instalada con el service worker viejo puede quedarse en una copia
    # guardada para siempre, porque el arreglo viaja dentro del archivo que no vuelve a bajar.
    with open(os.path.join(ROOT,"version.json"),"w",encoding="utf-8") as f:
        json.dump({"version": version, "fecha": time.strftime("%Y-%m-%d %H:%M")}, f)
    print(f"index.html generado: {len(tpl)} bytes (version {version})")

if __name__ == "__main__":
    build()
