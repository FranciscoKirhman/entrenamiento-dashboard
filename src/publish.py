#!/usr/bin/env python3
"""Sincroniza, reconstruye y publica en un solo paso — para que nada quede solo en local.

  python3 src/publish.py "mensaje del commit"

Hace, en orden:
  1. copia los .md de ~/Documents/Entrenamiento al repo (data/)
  2. recalcula los gráficos desde el historial (src/graficos.py)
  3. regenera index.html desde src/
  4. commit + push a GitHub
"""
import glob, json, os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.expanduser("~/Documents/Entrenamiento")

def run(*a, **k):
    r = subprocess.run(a, cwd=ROOT, capture_output=True, text=True, **k)
    if r.returncode: sys.exit(f"FALLO: {' '.join(a)}\n{r.stderr}{r.stdout}")
    return r.stdout.strip()

def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else "actualiza tablero"
    if os.path.isdir(DOCS):
        os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
        for f in glob.glob(os.path.join(DOCS, "*.md")):
            dst = os.path.join(ROOT, "data", os.path.basename(f))
            if not (os.path.exists(dst) and open(f,'rb').read() == open(dst,'rb').read()):
                shutil.copy2(f, dst); print("sincronizado:", os.path.basename(f))
    sys.path.insert(0, os.path.join(ROOT, "src"))
    import graficos
    cambios = graficos.actualiza(perfiles := json.load(open(graficos.PATH, encoding="utf-8")))
    if cambios:
        json.dump(perfiles, open(graficos.PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("gráficos:", *cambios, sep="\n  ")
    import build; build.build()
    if not run("git", "status", "--porcelain"):
        print("sin cambios que publicar"); return
    run("git", "add", "-A")
    run("git", "-c", "user.name=Francisco Kirhman",
        "-c", "user.email=francisco.osorio@ug.uchile.cl", "commit", "-m", msg)
    run("git", "push", "origin", "HEAD")
    print("publicado:", run("git", "log", "--oneline", "-1"))

if __name__ == "__main__":
    main()
