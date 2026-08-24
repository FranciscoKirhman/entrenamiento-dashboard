#!/usr/bin/env python3
"""Convierte los trazados SVG de MuscleMap (MIT, Melih Colpan) a JSON.

Fuente vendorizada en src/vendor/musclemap/ para que la conversion sea
reproducible sin red. Solo se leen los cuatro archivos de datos: son listas
de cadenas SVG, sin logica.

Salida: src/bodypaths.json
  {"male": {"front": {"viewBox": [x,y,w,h], "parts": {slug: [d, ...]}}, "back": {...}}, "female": {...}}
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "src", "vendor", "musclemap")
SALIDA = os.path.join(ROOT, "src", "bodypaths.json")

# de BodyPathData.swift; el origin se conserva porque los trazados estan en
# coordenadas de una lamina unica que contiene frente y espalda lado a lado
VIEWBOX = {
    ("male",   "front"): [0,   95, 727, 1280],
    ("male",   "back"):  [718, 95, 727, 1280],
    ("female", "front"): [0,   0,  650, 1450],
    ("female", "back"):  [823, 0,  650, 1450],
}

ARCHIVO = {
    ("male",   "front"): "MaleFrontPaths.swift",
    ("male",   "back"):  "MaleBackPaths.swift",
    ("female", "front"): "FemaleFrontPaths.swift",
    ("female", "back"):  "FemaleBackPaths.swift",
}

# camelCase de Swift -> slug con guion, igual que el rawValue del enum BodySlug
def a_slug(nombre):
    return re.sub(r'([a-z])([A-Z])', r'\1-\2', nombre).lower()

BLOQUE = re.compile(r'BodyPartPathData\(\s*slug:\s*\.(\w+)\s*,(.*?)\n        \)', re.S)
CADENA = re.compile(r'"((?:[^"\\]|\\.)*)"')

def extraer(ruta):
    txt = open(ruta, encoding="utf-8").read()
    # recorta el encabezado para no capturar comentarios de licencia
    txt = txt[txt.index("static let paths"):]
    partes = {}
    for m in BLOQUE.finditer(txt):
        slug = a_slug(m.group(1))
        cuerpo = m.group(2)
        trazos = [c.replace('\\"', '"') for c in CADENA.findall(cuerpo)]
        trazos = [t for t in trazos if t.startswith(("M", "m"))]   # descarta cualquier literal que no sea un path
        if not trazos:
            continue
        partes.setdefault(slug, []).extend(trazos)
    return partes

def main():
    salida = {}
    total = 0
    for (genero, lado), archivo in ARCHIVO.items():
        ruta = os.path.join(VENDOR, archivo)
        if not os.path.exists(ruta):
            sys.exit("falta " + ruta)
        partes = extraer(ruta)
        if not partes:
            sys.exit("no se extrajo nada de " + archivo)
        total += sum(len(v) for v in partes.values())
        salida.setdefault(genero, {})[lado] = {
            "viewBox": VIEWBOX[(genero, lado)],
            "parts": partes,
        }
        print("%-6s %-5s  %2d partes, %3d trazados" % (genero, lado, len(partes), sum(len(v) for v in partes.values())))
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print("bodypaths.json: %d trazados, %d KB" % (total, os.path.getsize(SALIDA)//1024))

if __name__ == "__main__":
    main()
