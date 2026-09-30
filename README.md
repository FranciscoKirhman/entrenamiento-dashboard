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
| `src/graficos.py` | Recalcula los gráficos de carga y el volumen por músculo desde el historial. `build.py` falla si quedaron atrasados. |
| `src/hevy_sync.py` | Trae las sesiones nuevas desde la API de Hevy para los perfiles con Pro (clave en `~/.config/hevy/<perfil>.key`, fuera del repo). |
| `src/hevy_csv.py` | Lo mismo para quien no tiene Pro: importa la exportación CSV de Hevy que quede en `~/Downloads` o en `~/Documents/Entrenamiento/hevy_csv`. Reconoce de quién es por las sesiones ya registradas. |
| `src/publish.py` | Sincroniza los `.md` de `~/Documents/Entrenamiento`, recalcula los gráficos, reconstruye, commitea y sube — todo en un paso. |
| `src/musclemap_convert.py` | Convierte los trazados de MuscleMap (Swift) a `src/bodypaths.json`. |
| `src/bodypaths.json` | **Generado** — geometría del diagrama anatómico. |
| `src/vendor/musclemap/` | Copia de los datos de MuscleMap y su licencia MIT. |
| `data/*.md` | Registros históricos y documentos de perfil, en markdown. |
| `data/ajustes.json` | **Lo escribe el tablero** desde el teléfono: días sin registro, sesiones pendientes o recuperadas, opcionales saltados. Ver abajo. |

## Sesiones de Mipi (sin Hevy Pro)

La API de Hevy es solo para Pro, así que las sesiones de Mipi entran por la exportación:

1. En su teléfono: **Perfil → Ajustes → Exportar e importar datos → Exportar entrenamientos**.
2. Manda el `workout_data.csv` al Mac (AirDrop, WhatsApp o correo) y déjalo en `~/Downloads`.
3. `python3 src/publish.py "sesiones de Mipi"`: importa lo nuevo, reconstruye y publica.

El archivo trae el historial completo; solo entra lo posterior a la última sesión registrada, así
que se puede volver a exportar e importar sin duplicar nada.

## Ajustes desde el teléfono (`data/ajustes.json`)

El plan de `profiles.json` no se toca desde el teléfono. Encima se aplican, en orden, los ajustes
que la persona marca en el tablero, y se guardan en `data/ajustes.json` con la API de GitHub:

- **Sin registro en Hevy**: un día de entrenamiento de los últimos 6 días que no tiene sesión. Se
  responde *Sí, falta subirla* (`hecho`), *No · la hago hoy* (`noHecho` + `recuperar`) o *No · otro
  día* (`noHecho`: la sesión queda pendiente).
- **Pendientes**: *Hacerla hoy*, *Otro día…* (`recuperar`) o *Descartar* (`descartar`).
  Recuperar una sesión el día X la pone en X y corre un día lo que venía desde X hasta el próximo
  descanso, que se ocupa.
- **Opcionales de la semana**: `opcSaltar`, `opcVolver`, `opcMover`.

Formato: `{"version": 1, "mopo": [...], "mipi": [...]}`. Cada ajuste trae `op`, `fecha`
(y `en` o `a` según el caso), `id`, `grupo`, `ts` y `txt`, la descripción en castellano. Un ajuste
que ya no calza con el plan (porque el plan lo incorporó o cambió por debajo) se ignora.

**Para actualizar el plan:** leer `data/ajustes.json` y aplicar esos cambios en `WEEKDAYS`. Después,
quitar del archivo los ajustes que quedaron incorporados, en el mismo commit. `publish.py` hace
`pull --rebase` antes de subir, porque el tablero pudo guardar commits entretanto.

**Conectar un teléfono:** el indicador ☁ de la barra superior abre las instrucciones. Se necesita
un token *fine-grained* de GitHub, con acceso solo a este repositorio y permiso *Contents: Read
and write*. Queda guardado solo en ese teléfono. Sin token, el tablero lee los ajustes de la
copia publicada y lo que se marque queda en ese teléfono hasta conectarlo.

## Cómo reconstruir y publicar

```bash
git clone https://github.com/FranciscoKirhman/entrenamiento-dashboard.git
cd entrenamiento-dashboard
python3 src/publish.py "actualiza tablero"   # sincroniza, reconstruye, commitea y sube
```

O paso a paso, si hace falta:

```bash
python3 src/musclemap_convert.py   # solo si cambia el diagrama anatómico
python3 src/graficos.py            # recalcula los gráficos desde el historial
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
- **Mopo y Mipi entrenan juntos: los planes se coordinan.** Los días firmes de ella
  coinciden con días de él, y las máquinas que comparten se marcan con 🤝 para
  alternar el pin.
- **Espalda baja: hay dos máquinas.** La de glúteo se anota en Hevy como
  *Back Extension (Weighted Hyperextension)*; la de erector espinal, como
  *Back Extension (Machine)*. En la de erector se levanta más peso: sus cargas no
  se comparan ni sirven para prescribir la otra.
- **No hay discos de 1,25 kg.** Toda carga con barra o Smith sube de a 5 kg;
  `build.py` lo verifica.

## Créditos

El diagrama anatómico usa los trazados de
[MuscleMap](https://github.com/melihcolpan/MuscleMap), de Melih Colpan,
publicado bajo licencia **MIT**. Los cuatro archivos de datos originales y el
texto de la licencia están en `src/vendor/musclemap/`; `src/musclemap_convert.py`
los pasa de Swift a JSON sin alterar la geometría.
