# Pico y Placa BGA — Guía de Arquitectura y Mantenimiento

> Última actualización: 12 de junio de 2026  
> Responsable: Convertix

---

## 1. Arquitectura general

```
┌──────────────────────┐
│   Usuario (navegador) │
└──────────┬───────────┘
           │ HTTPS
           ▼
┌──────────────────────┐      ┌────────────────────────────┐
│  Frontend (Vercel)    │─────▶│  Worker API (Cloudflare)     │
│  Vanilla JS + Vite    │      │  TypeScript + postgres.js    │
│  Motion One           │      │  Rate limit: 100 req/min     │
│  Outfit font          │      │  Read-only queries           │
└──────────────────────┘      └─────────────┬──────────────┘
                                            │ TCP (TLS)
                                            ▼
                               ┌────────────────────────────┐
                               │  Supabase (PostgreSQL 15)    │
                               │  3 tablas:                   │
                               │  - rotations                 │
                               │  - exception_overrides       │
                               │  - holidays                  │
                               └─────────────┬──────────────┘
                                             │
                               ┌─────────────┴──────────────┐
                               │  Scraper (Python)            │
                               │  BeautifulSoup + httpx       │
                               │  Asistido manualmente        │
                               │  Corre en GitHub Actions     │
                               └─────────────────────────────┘
```

### 1.1 Capas

| Capa | Qué hace | Dónde vive |
|------|----------|------------|
| **Frontend** | Muestra los dígitos del día, formulario de consulta, resultado | Vercel (auto-deploy desde GitHub) |
| **Worker API** | Recibe `placa + fecha + municipio`, consulta Supabase, devuelve si hay restricción | Cloudflare Workers |
| **Base de datos** | Guarda rotaciones trimestrales, excepciones, festivos | Supabase |
| **Scraper** | Extrae datos de la página de la DTB y los guarda en Supabase | Python local + GitHub Actions |

### 1.2 Flujo de una consulta

```
Usuario ingresa placa ABC123, fecha 2026-06-12, municipio bucaramanga
  │
  ▼
Frontend: extrae último dígito → 3
  │
  ▼
GET /v1/restriccion?municipio=bucaramanga&fecha=2026-06-12&placa=ABC123
  │
  ▼
Worker API:
  1. ¿Hay exception_override para bucaramanga el 2026-06-12? → No
  2. ¿Es festivo o domingo? → No (es viernes)
  3. Busca rotation vigente: valid_from ≤ 2026-06-12 ≤ valid_to
  4. raw_payload.weekdays.viernes = [7, 8]
  5. ¿El dígito 3 está en [7, 8]? → No
  6. Responde: { restricted: false, last_digit: 3 }
  │
  ▼
Frontend: muestra "Sin restricción — Hoy podés circular libremente"
```

---

## 2. Base de datos: las 3 tablas

### 2.1 `rotations` — La rotación trimestral

Es la tabla **principal**. Una fila por municipio por trimestre.

```sql
CREATE TABLE rotations (
    id           uuid PRIMARY KEY,
    municipality text NOT NULL,          -- 'bucaramanga', 'floridablanca', 'giron', 'piedecuesta'
    valid_from   date NOT NULL,          -- inicio del trimestre
    valid_to     date NOT NULL,          -- fin del trimestre
    raw_payload  jsonb NOT NULL,         -- el JSON con los dígitos
    source_url   text NOT NULL,          -- URL de la fuente oficial
    scraped_at   timestamptz NOT NULL    -- cuándo se guardó
);
```

**El `raw_payload` tiene esta forma:**

```json
{
  "weekdays": {
    "lunes": [9, 0],
    "martes": [1, 2],
    "miércoles": [3, 4],
    "jueves": [5, 6],
    "viernes": [7, 8]
  },
  "saturday_calendar": {
    "27": [1, 2],
    "28": [3, 4],
    "29": [5, 6],
    "30": [7, 8],
    "31": [9, 0],
    "32": [1, 2],
    "33": [3, 4],
    "34": [5, 6],
    "35": [7, 8]
  }
}
```

- `weekdays`: dígitos **fijos** de lunes a viernes durante TODO el trimestre.
- `saturday_calendar`: dígitos que **rotan cada sábado**. La clave es el número de semana ISO (27, 28, ...). Se mapean las semanas que caen dentro del trimestre.

### 2.2 `exception_overrides` — Excepciones (suspensiones)

Cuando la DTB anuncia que **no hay restricción** en una fecha específica (ej: Semana Santa, día cívico).

```sql
CREATE TABLE exception_overrides (
    id           uuid PRIMARY KEY,
    municipality text NOT NULL,
    date         date NOT NULL,          -- fecha exacta sin restricción
    reason       text NOT NULL,          -- "Semana Santa", "Día del taxista"
    source_url   text NOT NULL,
    scraped_at   timestamptz NOT NULL
);
```

Esta tabla se consulta **antes** que `rotations`. Si existe un override para la fecha, el sistema responde `restricted: false` sin importar lo que diga la rotación.

### 2.3 `holidays` — Festivos colombianos

```sql
CREATE TABLE holidays (
    date DATE PRIMARY KEY,
    name TEXT NOT NULL
);
```

Tabla estática con todos los festivos de Colombia. Domingos no se guardan (son implícitos: `dayOfWeek === 0`). Esta tabla casi nunca cambia — solo si el gobierno modifica el calendario de festivos.

---

## 3. Mantenimiento trimestral — PASO A PASO

**Frecuencia**: cada 3 meses, cuando la DTB publica la nueva resolución.  
**Tiempo estimado**: 15 minutos.  
**Lo que necesitás**: acceso al SQL Editor de Supabase.

### Paso 1: Conseguir la nueva infografía de la DTB

La Dirección de Tránsito de Bucaramanga (DTB) publica una infografía oficial cada trimestre. Buscala en:

- [https://transitobucaramanga.gov.co/dtb/](https://transitobucaramanga.gov.co/dtb/)
- O en el Twitter/X oficial: [@TransitoBGA](https://twitter.com/TransitoBGA)

La infografía muestra una tabla como esta:

```
PICO Y PLACA — ABRIL 6 A JULIO 4 DE 2026

LUNES       9 y 0
MARTES      1 y 2
MIÉRCOLES   3 y 4
JUEVES      5 y 6
VIERNES     7 y 8

SÁBADOS (rotan semanalmente):
Semana 27: 1 y 2
Semana 28: 3 y 4
...
```

### Paso 2: Identificar las fechas del trimestre

La resolución dice algo como *"desde el 6 de abril hasta el 4 de julio de 2026"*. Convertilo a `YYYY-MM-DD`:

- `valid_from`: `2026-04-06`
- `valid_to`: `2026-07-04`

### Paso 3: Armar el `raw_payload` para semana (lunes a viernes)

La parte `weekdays` es fija TODO el trimestre. Siguiendo el ejemplo de arriba:

```json
"weekdays": {
  "lunes": [9, 0],
  "martes": [1, 2],
  "miércoles": [3, 4],
  "jueves": [5, 6],
  "viernes": [7, 8]
}
```

> ⚠️ **Atención**: cada trimestre la DTB **corre los dígitos un par**. No asumas que el próximo trimestre va a tener los mismos pares.

### Paso 4: Armar el `saturday_calendar`

Los sábados **rotan cada semana**. La DTB publica un calendario con los dígitos por semana.

Lo CRÍTICO acá es mapear correctamente los **números de semana ISO** a los dígitos. La DTB suele numerar las semanas del 1 al 13 (semanas del trimestre), pero el sistema usa **semanas ISO 8601** (número de semana del año).

**Ejemplo de conversión para Q2 2026:**

| Semana DTB | Sábado (fecha) | Semana ISO | Dígitos |
|------------|----------------|------------|---------|
| 1 | 11 abr 2026 | 15 | 9 y 0 |
| 2 | 18 abr 2026 | 16 | 1 y 2 |
| 3 | 25 abr 2026 | 17 | 3 y 4 |
| ... | ... | ... | ... |

Para encontrar la semana ISO de una fecha, usá [https://weeknumber.com](https://weeknumber.com) o en JavaScript: `new Date('2026-04-11').getISOWeek()`.

### Paso 5: Ejecutar el SQL en Supabase

Abrí el [SQL Editor de Supabase](https://supabase.com/dashboard/project/dziwtdxovsmbbhhwhmgg) y ejecutá:

```sql
-- 1. Borrar rotaciones viejas del municipio
DELETE FROM rotations WHERE municipality = 'bucaramanga';

-- 2. Insertar la nueva rotación
INSERT INTO rotations (municipality, valid_from, valid_to, raw_payload, source_url)
VALUES (
  'bucaramanga',
  '2026-04-06',     -- ← fecha de inicio del trimestre
  '2026-07-04',     -- ← fecha de fin del trimestre
  '{
    "weekdays": {
      "lunes": [9, 0],
      "martes": [1, 2],
      "miércoles": [3, 4],
      "jueves": [5, 6],
      "viernes": [7, 8]
    },
    "saturday_calendar": {
      "15": [9, 0],
      "16": [1, 2],
      "17": [3, 4],
      "18": [5, 6],
      "19": [7, 8],
      "20": [9, 0],
      "21": [1, 2],
      "22": [3, 4],
      "23": [5, 6],
      "24": [7, 8],
      "25": [9, 0],
      "26": [1, 2]
    }
  }'::jsonb,
  'https://transitobucaramanga.gov.co/dtb/'
);

-- 3. Repetir para los otros municipios
DELETE FROM rotations WHERE municipality = 'floridablanca';
INSERT INTO rotations (municipality, valid_from, valid_to, raw_payload, source_url)
VALUES ('floridablanca', '2026-04-06', '2026-07-04', '{"weekdays":{"lunes":[9,0],"martes":[1,2],"miércoles":[3,4],"jueves":[5,6],"viernes":[7,8]},"saturday_calendar":{"15":[9,0],"16":[1,2],"17":[3,4],"18":[5,6],"19":[7,8],"20":[9,0],"21":[1,2],"22":[3,4],"23":[5,6],"24":[7,8],"25":[9,0],"26":[1,2]}}'::jsonb, 'https://transitobucaramanga.gov.co/dtb/');

DELETE FROM rotations WHERE municipality = 'giron';
INSERT INTO rotations (municipality, valid_from, valid_to, raw_payload, source_url)
VALUES ('giron', '2026-04-06', '2026-07-04', '{"weekdays":{"lunes":[9,0],"martes":[1,2],"miércoles":[3,4],"jueves":[5,6],"viernes":[7,8]},"saturday_calendar":{"15":[9,0],"16":[1,2],"17":[3,4],"18":[5,6],"19":[7,8],"20":[9,0],"21":[1,2],"22":[3,4],"23":[5,6],"24":[7,8],"25":[9,0],"26":[1,2]}}'::jsonb, 'https://transitobucaramanga.gov.co/dtb/');

DELETE FROM rotations WHERE municipality = 'piedecuesta';
INSERT INTO rotations (municipality, valid_from, valid_to, raw_payload, source_url)
VALUES ('piedecuesta', '2026-04-06', '2026-07-04', '{"weekdays":{"lunes":[9,0],"martes":[1,2],"miércoles":[3,4],"jueves":[5,6],"viernes":[7,8]},"saturday_calendar":{"15":[9,0],"16":[1,2],"17":[3,4],"18":[5,6],"19":[7,8],"20":[9,0],"21":[1,2],"22":[3,4],"23":[5,6],"24":[7,8],"25":[9,0],"26":[1,2]}}'::jsonb, 'https://transitobucaramanga.gov.co/dtb/');
```

### Paso 6: Verificar que funcionó

Abrí [https://pico-y-placa-bga.vercel.app](https://pico-y-placa-bga.vercel.app) y verificá:

1. El hero de la página muestra los dígitos correctos para hoy
2. Hacé una consulta con una placa que SÍ debería estar restringida → debe salir rojo
3. Hacé una consulta con una placa que NO debería estar restringida → debe salir verde
4. Cambiá el municipio y verificá que también funcione

También podés verificar directo contra la API:

```
https://pico-y-placa-api.juanchob612.workers.dev/v1/schedule?municipio=bucaramanga
```

---

## 4. Agregar excepciones (suspensiones temporales)

Cuando la DTB anuncia un día sin restricción (Semana Santa, día cívico, etc.):

```sql
INSERT INTO exception_overrides (municipality, date, reason, source_url)
VALUES
  ('bucaramanga', '2026-04-02', 'Jueves Santo', 'https://transitobucaramanga.gov.co/dtb/'),
  ('bucaramanga', '2026-04-03', 'Viernes Santo', 'https://transitobucaramanga.gov.co/dtb/');
```

Repetí para cada municipio si aplica. La API chequea esta tabla **antes** de mirar la rotación, así que un override siempre gana.

---

## 5. Cómo funciona el scraper (modo semi-automático)

El scraper de Python (`python/scraper/scraper.py`) puede extraer automáticamente los dígitos desde una página HTML de la DTB. **Pero requiere intervención humana** porque:

1. Los selectores CSS de la página de la DTB cambian sin aviso
2. El formato de las infografías no siempre es machine-readable
3. La DTB a veces publica PDFs en lugar de HTML

### Para usar el scraper:

```bash
cd python
python -m scraper --source-url "https://transitobucaramanga.gov.co/dtb/" --municipio bucaramanga --dry-run
```

El flag `--dry-run` hace que solo **muestre** lo que encontró sin escribirlo en Supabase. Revisá la salida. Si los dígitos son correctos, corré sin `--dry-run`:

```bash
python -m scraper --source-url "https://transitobucaramanga.gov.co/dtb/" --municipio bucaramanga
```

### Cuándo usar el scraper vs SQL manual

| Situación | Usar |
|-----------|------|
| La infografía es un HTML estructurado legible | Scraper |
| La infografía es una imagen/PDF | SQL manual (Sección 3) |
| La página de la DTB cambió de diseño | SQL manual |
| Querés verificar antes de escribir | Scraper con `--dry-run` |

**Recomendación**: en la práctica, el 90% de las veces vas a usar el SQL manual. Es más rápido y no depende de que el scraper entienda el formato nuevo.

---

## 6. Gestión de festivos — revisión anual obligatoria

Los festivos colombianos **no vienen precargados** en la base de datos. Deben insertarse explícitamente mediante la migración de seed. La tabla `holidays` solo se puebla cuando ejecutás la migración `0004_seed_holidays_2026.sql` contra Supabase.

### Dónde están definidos

Los 18 festivos nacionales de Colombia para 2026 están definidos en:
```
supabase/migrations/0004_seed_holidays_2026.sql
```

Esta migración usa `ON CONFLICT (date) DO NOTHING`, así que es segura para re-ejecutar.

### Cómo agregar un festivo nuevo

**Opción A — Insert directo en Supabase (cambios puntuales):**

Si es un solo festivo nuevo y no querés tocar migraciones:
```sql
INSERT INTO holidays (date, name)
VALUES ('2027-07-01', 'Nuevo Festivo Nacional')
ON CONFLICT (date) DO NOTHING;
```

**Opción B — Agregar a la migración de seed (recomendado):**

Editá `supabase/migrations/0004_seed_holidays_2026.sql` y agregá la nueva fila al bloque `INSERT`. Esto deja trazabilidad en el repo.

### Revisión anual

⚠️ **Todos los años, antes del 15 de enero, verificá:**

1. Que los festivos del año nuevo estén en la tabla `holidays`
2. Que las fechas móviles (basadas en Semana Santa) sean correctas para ese año
3. Si creaste una nueva migración de seed para el año (ej: `000X_seed_holidays_2027.sql`), actualizá esta sección del documento

Los festivos de fecha fija (Año Nuevo, Día del Trabajo, Independencia, Batalla de Boyacá, Inmaculada Concepción, Navidad) nunca cambian. Los festivos móviles (Semana Santa, Ascensión, Corpus Christi, Sagrado Corazón) dependen de la fecha de Pascua y deben recalcularse cada año.

---

## 7. Troubleshooting

### "No tenemos datos de la rotación vigente"

**Causa**: no hay ninguna fila en `rotations` cuyo `valid_from ≤ hoy ≤ valid_to`.

**Solución**: revisá si las fechas del trimestre son correctas. A veces la DTB publica resoluciones con fechas raras (ej: "hasta el 5 de julio" cuando en realidad es "hasta el 4").

```sql
-- Ver qué rotaciones hay vigentes hoy
SELECT municipality, valid_from, valid_to
FROM rotations
WHERE valid_from <= CURRENT_DATE
  AND valid_to >= CURRENT_DATE;
```

### "Los sábados no funcionan bien"

**Causa**: el `saturday_calendar` usa semanas ISO incorrectas. La DTB numera las semanas del 1 al 13 pero el sistema usa semanas ISO (1-53 del año).

**Solución**: convertí manualmente cada sábado del trimestre a su semana ISO. Herramienta: [https://weeknumber.com](https://weeknumber.com).

### "Vercel no actualizó el frontend"

**Causa**: Vercel a veces no detecta el push si solo cambian archivos fuera de `frontend/`.

**Solución**: forzá un redeploy desde el dashboard de Vercel o hacé un commit vacío en `frontend/`:

```bash
git commit --allow-empty -m "chore: trigger vercel deploy"
git push
```

### "La API está lenta o no responde"

**Causa**: cold start del Worker (la conexión a Supabase se dropea después de 10s de inactividad).

**Solución**: la primera consulta del día puede tardar ~500ms extra. Las siguientes son rápidas. Si es recurrente, aumentá `idle_timeout` en `worker/wrangler.toml`.

---

## 8. Checklist de mantenimiento trimestral

- [ ] Conseguir la nueva infografía de la DTB
- [ ] Identificar `valid_from` y `valid_to` del nuevo trimestre
- [ ] Extraer los 5 pares de dígitos de lunes a viernes
- [ ] Extraer el calendario de sábados (dígitos por semana)
- [ ] Convertir semanas DTB → semanas ISO
- [ ] Armar el JSON `raw_payload`
- [ ] Ejecutar DELETE + INSERT en Supabase para los 4 municipios
- [ ] Verificar en [https://pico-y-placa-bga.vercel.app](https://pico-y-placa-bga.vercel.app)
- [ ] Verificar en la API: `/v1/schedule?municipio=bucaramanga`
- [ ] Verificar que el hero muestre los dígitos correctos para HOY

---

## 9. Referencias rápidas

| Recurso | URL |
|---------|-----|
| Sitio en producción | https://pico-y-placa-bga.vercel.app |
| API en producción | https://pico-y-placa-api.juanchob612.workers.dev |
| Supabase Dashboard | https://supabase.com/dashboard/project/dziwtdxovsmbbhhwhmgg |
| Repo GitHub | https://github.com/juancjerezm/pico-y-placa-bga |
| DTB (fuente oficial) | https://transitobucaramanga.gov.co/dtb/ |
| Conversor semana ISO | https://weeknumber.com |
