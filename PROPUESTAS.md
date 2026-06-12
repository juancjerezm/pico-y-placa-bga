# PROPUESTAS — Reemplazo del Scraper para Gestión de Datos

> Fecha: 12 de junio de 2026  
> Estado: **Para estudio y decisión**  
> Contexto: El scraper actual no puede acceder a las fuentes oficiales por protecciones anti-bot (Cloudflare, CAPTCHA). Se evalúa si matarlo y con qué reemplazarlo.

---

## 1. Diagnóstico: ¿qué hace el scraper hoy y qué no funciona?

### 1.1 Lo que el scraper intenta hacer

```
┌──────────────────────┐
│  DTB / picoyplacaya   │  ← fuente oficial con anti-bot
│  (HTML / Next.js)     │
└──────────┬───────────┘
           │ ❌ httpx bloqueado (403, CAPTCHA, Cloudflare)
           ▼
┌──────────────────────┐
│  Scraper (Python)     │
│  scraper/__main__.py  │  ← fetch → extraer JSON → upsert Supabase
│  scraper/scraper.py   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Supabase             │
│  tabla rotations      │
└──────────────────────┘
```

### 1.2 Lo que realmente hace el scraper (partes funcionales vs rotas)

| Componente | Funciona | Archivo | Líneas |
|------------|----------|---------|--------|
| Fetch HTTP de la fuente | ❌ Bloqueado por anti-bot | `__main__.py:_fetch_html()` | ~100 |
| Parseo de dígitos desde texto | ✅ | `scraper.py:extract_rotation_digits()` | ~200 |
| Parseo de fechas (ISO, español) | ✅ | `scraper.py:extract_date_range()` | ~100 |
| Calendario de sábados | ✅ | `scraper.py:extract_saturday_calendar()` | ~150 |
| Upsert a Supabase | ✅ | `__main__.py:_upsert_rotations()` | ~40 |
| Logging estruturado | ✅ | `__main__.py:_log_run()` | ~15 |

**Conclusión**: el 80% del código (parseo) funciona. El 20% que NO funciona es justamente el paso 1 — acceder a la fuente. Sin ese paso, todo el pipeline es inútil.

### 1.3 Si matamos el scraper, ¿qué se pierde?

| Elemento | ¿Se pierde? | Explicación |
|----------|:----------:|-------------|
| `python/scraper/__main__.py` (278 líneas) | 🟡 Queda obsoleto | Entry point del CLI. Ya no se usaría. |
| `python/scraper/scraper.py` (495 líneas) | 🟡 Queda obsoleto | Parseo de HTML/artículos. Solo útil si scrapeamos. |
| `python/scraper/test_scraper.py` | 🟡 Tests de algo que no corre | Podemos archivarlo pero no borrarlo. |
| `.github/workflows/scraper.yml` | 🔴 Se para | El cron job de GitHub Actions deja de tener sentido. |
| `python/plate_parser/` | 🟢 **NO se pierde** | Independiente. Valida placas. Se usa para testing del parser. |
| `worker/` (API) | 🟢 **NO se toca** | La API solo lee Supabase. No depende del scraper. |
| `frontend/` | 🟢 **NO se toca** | El frontend consume la API. Cero relación con el scraper. |
| Supabase (tablas) | 🟢 **NO se toca** | Las tablas siguen igual. Solo cambia CÓMO se llenan. |
| Dependencias Python | 🟡 Se reducen | `beautifulsoup4` y `httpx` ya no se necesitarían. Solo queda `pytest`, `ruff`, `mypy` para el `plate_parser`. |

**Resumen**: matar el scraper no rompe NADA de producción. La API, el frontend y Supabase siguen funcionando exactamente igual. Solo cambia **cómo llegan los datos a la tabla `rotations`**.

---

## 2. Las 3 opciones para reemplazar el scraper

### Opción A: CSV + script generador de SQL

```
┌─────────────────┐      ┌──────────────────┐      ┌──────────────┐
│  Excel / Sheets   │─────▶│  python gen_sql   │─────▶│  Supabase     │
│  (editás a mano)  │      │  (lee CSV → SQL)  │      │  (copiar/pegar)│
└─────────────────┘      └──────────────────┘      └──────────────┘
```

**Cómo funciona**: Editás un CSV (o Google Sheets exportado) con una fila por ciudad. El script genera automáticamente el `raw_payload` JSON, las fechas ISO, y el calendario de sábados. Escupe el SQL listo para copiar y pegar en el SQL Editor de Supabase.

**Formato del CSV**:
```csv
ciudad,lunes,martes,miercoles,jueves,viernes,desde,hasta,sabados_json
Bucaramanga,"9,0","1,2","3,4","5,6","7,8",2026-04-06,2026-07-04,"{15:[9,0],16:[1,2],...}"
Cali,"1,2","3,4","5,6","7,8","9,0",2026-04-01,2026-06-30,"{14:[1,2],15:[3,4],...}"
```

| ✅ Ventajas | ❌ Desventajas |
|------------|---------------|
| Setup en 10 minutos | Dos pasos: editar CSV + correr script |
| El CSV se edita en cualquier lado | El sábado requiere dar fechas en vez de números mágicos |
| Sin autenticación, sin APIs externas | No es "vivo" — cada trimestre requiere acción manual |
| Script simple (~50 líneas de Python) | |
| Cero riesgo de rotura a futuro | |
| Ideal para 1 persona manteniendo | |

**Código necesario**: ~50 líneas de Python. Un archivo nuevo `python/generate_sql.py`.

**Costo mensual**: $0.

---

### Opción B: Google Sheets → Supabase automático (vía GitHub Actions)

```
┌─────────────────┐      ┌──────────────────────┐      ┌──────────────┐
│  Google Sheets    │─────▶│  GitHub Actions       │─────▶│  Supabase     │
│  "Panel de control"│     │  cron: cada 1 hora    │      │  automático   │
│  (vos editás)     │      │  Lee Sheets API       │      │              │
└─────────────────┘      └──────────────────────┘      └──────────────┘
```

**Cómo funciona**: 
- Una planilla de Google Sheets oficia de "panel de administración"
- Un script de Python (corriendo en GitHub Actions cada 1 hora) lee la planilla vía Google Sheets API
- Si detecta cambios contra lo que ya está en Supabase, escribe automáticamente
- La planilla tiene una columna `sync_status` que dice "pendiente" / "sincronizado"

**Formato de la planilla**:

| ciudad | lunes | martes | miércoles | jueves | viernes | desde | hasta | sábados (fecha=digitos) | sync_status |
|--------|-------|--------|-----------|--------|---------|-------|------|------------------------|-------------|
| Bucaramanga | 9,0 | 1,2 | 3,4 | 5,6 | 7,8 | 2026-04-06 | 2026-07-04 | 2026-04-11=9,0; 2026-04-18=1,2; ... | sincronizado |

| ✅ Ventajas | ❌ Desventajas |
|------------|---------------|
| Editás como Excel, sin tocar código | Setup único: Google Service Account (~10 min) |
| Varias personas pueden editar a la vez | Depende de Google Sheets API (gratis: 500 req/100s) |
| Version history automático (Google) | Si Google cambia la API, hay que actualizar el script |
| Sincronización automática cada hora | |
| El "panel" es tan simple como una planilla | |
| Escala a 100+ ciudades sin esfuerzo | |

**Código necesario**: ~150 líneas de Python + 1 archivo de workflow de GitHub Actions.

**Setup único**: Crear una Google Cloud Service Account, habilitar Sheets API, compartir la planilla con la service account, guardar la key como secreto de GitHub.

**Costo mensual**: $0 (GitHub Actions free tier + Google Sheets API free tier).

---

### Opción C: Supabase directo con formulario web (dashboard interno)

```
┌──────────────────────────┐      ┌──────────────┐
│  Admin Dashboard (web)    │─────▶│  Supabase     │
│  Formulario HTML simple   │      │  directo       │
│  /admin en el frontend    │      │               │
└──────────────────────────┘      └──────────────┘
```

**Cómo funciona**: 
- Una ruta protegida en el frontend (`/admin`) con un formulario
- Campos: ciudad, fechas, dígitos semanales, calendario de sábados
- Un botón "Guardar" que escribe directo a Supabase vía API REST
- Protegido con una contraseña simple o token en URL

| ✅ Ventajas | ❌ Desventajas |
|------------|---------------|
| Sin pasos intermedios — editás y guardás | Hay que construir el dashboard |
| Validación en tiempo real (no podés guardar datos mal) | Hay que mantenerlo (cambios de Supabase, CORS) |
| El más rápido para el que mantiene | Overkill para < 20 ciudades |
| Queda integrado al proyecto | Agrega superficie de ataque (necesita auth) |

**Código necesario**: ~200 líneas (HTML + JS + CSS) + middleware de auth simple.

**Costo mensual**: $0.

---

## 3. Matriz de decisión

| Criterio | Opción A (CSV) | Opción B (Sheets) | Opción C (Dashboard) |
|----------|:---:|:---:|:---:|
| **Facilidad de setup** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Facilidad de uso diario** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Escala a 50+ ciudades** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Colaboración multi-persona** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Mantenimiento futuro** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Resistencia a roturas** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Costo mensual** | $0 | $0 | $0 |
| **Tiempo de implementación** | 1 hora | 3 horas | 6 horas |

---

## 4. Recomendación según escenario

### Si te quedás con ≤ 10 ciudades → Opción A (CSV + script)

No hay razón para meter infraestructura extra. El CSV lo editás en 2 minutos cada 3 meses. El script te ahorra el 90% del trabajo (generar JSON a mano). Es la opción más simple y la que menos se puede romper.

### Si planeás cubrir Colombia (30-100+ ciudades) → Opción B (Google Sheets)

La planilla es colaborativa, cualquiera del equipo puede mantener los datos de su ciudad, y la sincronización es automática. El setup único de la service account vale la pena a esa escala.

### Si esto se convierte en un producto pago con clientes → Opción C (Dashboard)

Solo si tenés clientes que necesitan autogestionar sus propias rotaciones. Para uso interno, es overkill.

---

## 5. Respuesta directa a tus preguntas

> "El scraper no está funcionando, ¿lo matamos?"

**Sí**. Hoy no funciona, y aunque funcionara, se corre 4 veces al año. Es sobre-ingeniería para el caso de uso real.

> "¿Cuál de los 3 servicios se perdería?"

**Ninguno de producción**. Lo único que se pierde es el pipeline automático de extracción HTML → Supabase, que YA ESTÁ ROTO. La API Worker, el frontend, y Supabase siguen funcionando exactamente igual. La tabla `rotations` sigue existiendo — solo cambia quién la llena (un humano en vez de un bot).

El único código que queda obsoleto es `python/scraper/`. El `plate_parser` se mantiene independiente.

> "¿Overkill?"

El scraper actual con 700+ líneas de Python, tests, GitHub Actions, y dependencias (httpx, BeautifulSoup) para algo que se usa 4 veces al año y ENCIMA no funciona → **overkill total**.

> "Yo veo a pin: base de datos y frontend"

Exacto. La esencia del sistema son 2 cosas: **Supabase** (datos) y **Frontend** (interfaz). El Worker API es un pasamanos read-only entre ambos. Todo lo demás (scraper, scripts) son herramientas auxiliares para **llenar** Supabase. Lo importante es que llenar Supabase sea fácil y no requiera saber SQL ni JSON.

---

## 6. Próximo paso

Elegí una opción (A, B, o C) y cuando quieras la implementamos. Si tenés dudas, revisalas tranqui — están todas documentadas acá.
