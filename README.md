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
| `src/parse_log.py` | Convierte un registro markdown a JSON de sesiones (sirve para ambos perfiles). |
| `src/parse_mopo.py` | Versión antigua, específica de Mopo. |
| `src/publish.py` | Sincroniza los `.md` de `~/Documents/Entrenamiento`, reconstruye, commitea y sube — todo en un paso. |
| `src/musclemap_convert.py` | Convierte los trazados de MuscleMap (Swift) a `src/bodypaths.json`. |
| `src/bodypaths.json` | **Generado** — geometría del diagrama anatómico. |
| `src/vendor/musclemap/` | Copia de los datos de MuscleMap y su licencia MIT. |
| `data/*.md` | Registros históricos y documentos de perfil, en markdown. |

## Cómo reconstruir y publicar

```bash
git clone https://github.com/FranciscoKirhman/entrenamiento-dashboard.git
cd entrenamiento-dashboard
python3 src/publish.py "actualiza tablero"   # sincroniza, reconstruye, commitea y sube
```

O paso a paso, si hace falta:

```bash
python3 src/musclemap_convert.py   # solo si cambia el diagrama anatómico
python3 src/build.py               # regenera index.html
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

## Créditos

El diagrama anatómico usa los trazados de
[MuscleMap](https://github.com/melihcolpan/MuscleMap), de Melih Colpan,
publicado bajo licencia **MIT**. Los cuatro archivos de datos originales y el
texto de la licencia están en `src/vendor/musclemap/`; `src/musclemap_convert.py`
los pasa de Swift a JSON sin alterar la geometría.
