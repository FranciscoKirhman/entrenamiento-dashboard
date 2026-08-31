#!/usr/bin/env python3
"""Reconstruye index.html desde src/. Ejecutar desde la raiz del repo:  python3 src/build.py"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "src")

FONTS = {"OSWALD_600":"oswald-600","OSWALD_700":"oswald-700",
         "PLEXSANS_400":"plexsans-400","PLEXSANS_500":"plexsans-500","PLEXSANS_600":"plexsans-600",
         "PLEXMONO_400":"plexmono-400","PLEXMONO_500":"plexmono-500"}

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
    tpl = tpl.replace("__PROFILES_JSON__", json.dumps(profiles, ensure_ascii=False))
    cuerpos = json.load(open(os.path.join(SRC,"bodypaths.json"), encoding="utf-8"))
    tpl = tpl.replace("__BODYPATHS_JSON__", json.dumps(cuerpos, ensure_ascii=False, separators=(",",":")))
    assert "{{" not in tpl and "__PROFILES_JSON__" not in tpl and "__BODYPATHS_JSON__" not in tpl, "quedaron placeholders sin reemplazar"
    assert 'name="viewport"' in tpl, "falta el meta viewport (rompe la vista movil)"
    out = os.path.join(ROOT,"index.html")
    open(out,"w",encoding="utf-8").write(tpl)
    print(f"index.html generado: {len(tpl)} bytes")

if __name__ == "__main__":
    build()
