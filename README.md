# Tablero de entrenamiento — Mopo y Mipi

Publicado en **https://franciscokirhman.github.io/entrenamiento-dashboard/**

Todo lo necesario para reconstruir el tablero vive en este repositorio. No hay
nada indispensable fuera de acá: si se pierde la máquina o el directorio temporal
de una sesión, basta con clonar este repo.

## Estructura

| Ruta | Qué es |
|---|---|
| `index.html` | El tablero publicado. **Generado** — no editar a mano. |
| `src/dashboard.template.html` | Plantilla con los marcadores `{{FUENTES}}` y `__PROFILES_JSON__`. |
| `src/profiles.json` | **La fuente de verdad de los datos**: perfiles, rutina semanal, músculos, gráficos e historial de ambos. |
| `src/fonts/*.b64` | Fuentes en base64 (van embebidas, el tablero no llama a ninguna CDN). |
| `src/build.py` | Genera `index.html` desde la plantilla + `profiles.json`. |
| `src/parse_mopo.py` | Convierte el registro markdown de Mopo a JSON de sesiones. |
| `data/*.md` | Registros históricos y documentos de perfil, en markdown. |

## Cómo reconstruir y publicar

```bash
git clone https://github.com/FranciscoKirhman/entrenamiento-dashboard.git
cd entrenamiento-dashboard
python3 src/build.py          # regenera index.html
git add -A && git commit -m "actualiza tablero" && git push
```

GitHub Pages sirve `index.html` desde la rama `main`; la propagación tarda
menos de un minuto.

## Reglas del proyecto

- **Los datos reales no se inventan nunca.** Cada serie del historial viene
  copiada de Hevy. Los volúmenes se cruzan contra el total oficial de la app
  antes de dar una sesión por buena.
- **Las fechas ambiguas se preguntan, no se deducen.**
- Las molestias leves se registran tal cual, sin convertirlas en restricciones
  del entrenamiento salvo que la persona lo pida.
