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
| `.github/workflows/hevy.yml` | Cada 15 minutos trae de Hevy las sesiones nuevas y republica el tablero. Ver abajo. |

## Sesiones de Mipi (sin Hevy Pro)

La API de Hevy es solo para Pro, así que las sesiones de Mipi entran por la exportación:

1. En su teléfono: **Perfil → Ajustes → Exportar e importar datos → Exportar entrenamientos**.
2. Manda el `workout_data.csv` al Mac (AirDrop, WhatsApp o correo) y déjalo en `~/Downloads`.
3. `python3 src/publish.py "sesiones de Mipi"`: importa lo nuevo, reconstruye y publica.

El archivo trae el historial completo; solo entra lo posterior a la última sesión registrada, así
que se puede volver a exportar e importar sin duplicar nada.

## El plan se ajusta solo con Hevy

No hay botones para mover el plan: lo registrado en Hevy decide.

- **Qué sesión se hizo.** Cada sesión registrada se asigna a la del plan que más se le parece por
  ejercicios, entre una semana antes y tres días después de su fecha. Así se reconoce una sesión
  recuperada (la del lunes hecha el miércoles) o adelantada.
- **Qué queda pendiente.** Una sesión del plan que pasó sin registro queda pendiente y va primero:
  desde hoy, lo que venía se corre un día por cada pendiente, hasta que un descanso la absorbe.
  Una pendiente se deja de arrastrar al pasar una semana, o si la misma sesión ya se hizo después o
  toca hoy o mañana. Los opcionales que no se hicieron no quedan pendientes.
- **Qué se sabe.** Solo cuenta como no hecho lo que se sabe:
  - **Mopo:** GitHub trae sus sesiones cada 15 minutos (`hevy.yml`). El tablero consulta la última
    corrida exitosa del workflow y, si tiene menos de 2 horas, da por sabidos todos los días hasta ayer.
  - **Mipi:** sus sesiones entran con la exportación CSV, así que después de su último registro no se
    da nada por perdido.
- **Cuando hay una pendiente**, Hoy muestra las dos opciones (la pendiente y la del día) y qué pasa
  con cada una. Se hace cualquiera, se registra en Hevy y el plan se recalcula.

El plan de `profiles.json` sigue siendo la base: ajustarlo a mano (por ejemplo, reordenar una semana)
funciona igual, y lo registrado en Hevy se sigue asignando encima.

### Sincronización automática (`.github/workflows/hevy.yml`)

Corre `src/hevy_sync.py` cada 15 minutos. Si hay algo nuevo, lo agrega a `data/` y a `profiles.json`,
recalcula los gráficos, reconstruye y sube. La clave de Hevy va como secreto del repositorio, nunca
en el código:

```bash
gh secret set HEVY_API_KEY_MOPO --repo FranciscoKirhman/entrenamiento-dashboard < ~/.config/hevy/mopo.key
```

Sin el secreto, la corrida falla a propósito: el tablero cuenta como "al día" solo las corridas
exitosas. `publish.py` trae lo que haya subido GitHub antes de tocar nada, y `hevy_sync.py` en el Mac
copia al registro canónico (`~/Documents/Entrenamiento`) los bloques que la nube ya trajo, sin
duplicarlos en `SESSIONS_FULL`.

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
