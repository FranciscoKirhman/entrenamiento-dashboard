#!/usr/bin/env python3
"""Reconstruye index.html desde src/. Ejecutar desde la raiz del repo:  python3 src/build.py"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "src")

FONTS = {"OSWALD_600":"oswald-600","OSWALD_700":"oswald-700",
         "PLEXSANS_400":"plexsans-400","PLEXSANS_500":"plexsans-500","PLEXSANS_600":"plexsans-600",
         "PLEXMONO_400":"plexmono-400","PLEXMONO_500":"plexmono-500"}

def build():
    tpl = open(os.path.join(SRC,"dashboard.template.html"), encoding="utf-8").read()
    for key, slug in FONTS.items():
        b64 = open(os.path.join(SRC,"fonts",slug+".b64"), encoding="utf-8").read().strip()
        tpl = tpl.replace("{{"+key+"}}", b64)
    # diagrama del cuerpo (opcional): si existe src/body.svg se inserta, si no queda vacio
    body = ""
    bpath = os.path.join(SRC, "body.svg")
    if os.path.exists(bpath):
        body = open(bpath, encoding="utf-8").read().strip().replace("\n", " ")
        body = body.replace("\\", "\\\\").replace("'", "\\'")
    tpl = tpl.replace("__BODY_SVG__", body)

    profiles = json.load(open(os.path.join(SRC,"profiles.json"), encoding="utf-8"))
    tpl = tpl.replace("__PROFILES_JSON__", json.dumps(profiles, ensure_ascii=False))
    assert "{{" not in tpl and "__PROFILES_JSON__" not in tpl and "__BODY_SVG__" not in tpl, "quedaron placeholders sin reemplazar"
    assert 'name="viewport"' in tpl, "falta el meta viewport (rompe la vista movil)"
    out = os.path.join(ROOT,"index.html")
    open(out,"w",encoding="utf-8").write(tpl)
    print(f"index.html generado: {len(tpl)} bytes")

if __name__ == "__main__":
    build()
