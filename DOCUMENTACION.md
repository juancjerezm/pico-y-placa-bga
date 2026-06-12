# Pico y Placa Bucaramanga — Documentación

> **URL**: https://pico-y-placa-bga.vercel.app  
> **API**: https://pico-y-placa-api.juanchob612.workers.dev  
> **Repo**: https://github.com/juancjerezm/pico-y-placa-bga  
> **Última actualización**: 12 de junio de 2026

---

## 1. Arquitectura

```
Frontend (Vercel) → Worker API (Cloudflare) → Supabase (PostgreSQL)
      ↑                      ↑                       ↑
  Vanilla JS            TypeScript              Datos oficiales
  Vite + Motion One    postgres.js              DTB Bucaramanga
```

| Capa | Tecnología | Host | Función |
|------|-----------|------|---------|
| Frontend | Vite + vanilla JS + Motion One | Vercel | Interfaz de usuario |
| API | TypeScript + postgres.js | Cloudflare Workers | Consultas read-only |
| Base de datos | PostgreSQL | Supabase | Rotaciones, excepciones, festivos |
| Datos | Manual (SQL) + propuesta de reemplazo | — | Alimentación trimestral (ver PROPUESTAS.md) |

---

## 2. URLs del sistema

| Servicio | URL |
|----------|-----|
| **Frontend (producción)** | https://pico-y-placa-bga.vercel.app |
| **API (producción)** | https://pico-y-placa-api.juanchob612.workers.dev |
| **Supabase Dashboard** | https://supabase.com/dashboard/project/dziwtdxovsmbbhhwhmgg |
| **GitHub Repo** | https://github.com/juancjerezm/pico-y-placa-bga |

---

## 3. Endpoints de la API

### `GET /v1/restriccion`
```
?municipio=bucaramanga&fecha=2026-06-10&placa=ABC123

→ 200: { restricted: true/false, last_digit: 3, formato_detectado: "particular", ... }
→ 400: { error: "bad_plate" | "bad_date" | "bad_municipio" }
→ 404: { error: "rotation_unknown" }
```

### `GET /v1/schedule`
```
?municipio=bucaramanga

→ 200: { current: {...} | null, next: {...} | null, message: null | "rotation_unknown" }
```

---

## 4. Cómo funciona la rotación

### Regla oficial (Resolución 854 del 30/12/2025 — DTB)

**Trimestre Q2 2026** (abril 6 a julio 4):

| Día | Dígitos restringidos |
|-----|---------------------|
| Lunes | 9 y 0 |
| Martes | 1 y 2 |
| Miércoles | 3 y 4 |
| Jueves | 5 y 6 |
| Viernes | 7 y 8 |

- **Lunes a viernes**: dígitos **FIJOS** durante todo el trimestre
- **Sábados**: rotan **semanalmente** según calendario oficial DTB
- **Domingos y festivos**: sin restricción
- **Horario**: 6:00 AM - 8:00 PM (lunes a viernes), 9:00 AM - 1:00 PM (sábados)

### Cambio trimestral
Cada 3 meses la DTB publica una nueva resolución que **corre los dígitos un par**. Al cambiar el trimestre:
1. Obtener la nueva infografía oficial de la DTB
2. Actualizar la tabla `rotations` en Supabase con los nuevos `valid_from`, `valid_to`, y `raw_payload`
3. El sistema se ajusta automáticamente

---

## 5. Cómo actualizar los datos (cada 3 meses)

> 📘 **Guía detallada paso a paso**: ver [`MANTENIMIENTO.md`](./MANTENIMIENTO.md)

```sql
-- Ejemplo para Q3 2026 (hipotético)
DELETE FROM rotations;

INSERT INTO rotations (municipality, valid_from, valid_to, raw_payload, source_url)
VALUES
  ('bucaramanga', '2026-07-06', '2026-10-02', 
   '{"weekdays":{"lunes":[1,2],"martes":[3,4],"miércoles":[5,6],"jueves":[7,8],"viernes":[9,0]},"saturday_calendar":{"27":[1,2],"28":[3,4],"29":[5,6],"30":[7,8],"31":[9,0],"32":[1,2],"33":[3,4],"34":[5,6],"35":[7,8],"36":[9,0],"37":[1,2],"38":[3,4],"39":[5,6]}}', 
   'https://transitobucaramanga.gov.co/dtb/'),
  -- Repetir para floridablanca, giron, piedecuesta
;
```

---

## 6. Seguridad (Nivel 1 MVP)

| Capa | Medida |
|------|--------|
| Rate limiting | 100 req/min por IP |
| Headers | X-Content-Type-Options, X-Frame-Options, HSTS, Referrer-Policy |
| CORS | Allow all origins (API pública) |
| Logging | JSON estructurado (sin datos sensibles) |
| Secretos | Variables de entorno (.env gitignored) |
| HTTPS | Cloudflare + Vercel default |

---

## 7. Testing

| Suite | Tests | Cobertura |
|-------|-------|-----------|
| Plate parser (Python) | 42 | 100% |
| Scraper (Python) | 49 | 90% |
| Worker API (TypeScript) | 40 | Contract |
| Frontend (vanilla JS) | 56 | 8/8 REQ-FE |
| **Total** | **187** | **0 fallos** |

---

## 8. Optimizaciones de rendimiento (Jun 2026)

Para resolver la lentitud en la renderización de los dígitos del hero:

| Optimización | Archivo | Impacto |
|-------------|---------|---------|
| Cache del schedule trimestral en localStorage | `api.js` | Visitas repetidas: de ~600ms a ~0ms |
| Cálculo client-side de dígitos (sin API) | `api.js` | Los dígitos se computan con la fecha y el payload cacheado |
| Placeholder "···" con CSS pulse | `index.html` + `style.css` | El hero nunca está vacío mientras carga |
| Texto visible instantáneo, animación decorativa | `hero.js` | El número aparece en el frame 0, animación encima |

**Flujo optimizado**:
```
0ms    → "···" pulsando (placeholder nativo)
~5ms   → Cache hit: dígitos calculados en JS (0ms network)  
~15ms  → "5 - 6" visible + flip animation decorativa
```
(Antes: ~1150ms hasta ver los dígitos)

---

## 9. Documentación adicional

| Documento | Contenido |
|-----------|-----------|
| [`MANTENIMIENTO.md`](./MANTENIMIENTO.md) | Guía completa de arquitectura y paso a paso para actualizar datos cada trimestre |
| [`PROPUESTAS.md`](./PROPUESTAS.md) | Análisis de 3 opciones para reemplazar el scraper (que no funciona por anti-bot). Para estudio y decisión. |

---

## 10. Repositorio y ramas

- **Rama principal**: `main`
- **SDD**: `openspec/specs/` (4 specs), `openspec/changes/archive/` (artefactos archivados)
- **Commits**: 11 commits con conventional commits

---

## 11. Mantenimiento

| Frecuencia | Acción |
|------------|--------|
| **Cada 3 meses** | Actualizar rotación en Supabase — ver [`MANTENIMIENTO.md`](./MANTENIMIENTO.md) |
| **Cuando se publique** | Agregar exception_overrides si hay suspensiones (Semana Santa, etc.) |
| **Cuando falle** | Revisar logs en Cloudflare Dashboard / Supabase |

> ⚠️ **El scraper automático NO funciona** (bloqueado por anti-bot en las fuentes). Los datos se ingresan manualmente vía SQL en Supabase. Se está evaluando un reemplazo — ver [`PROPUESTAS.md`](./PROPUESTAS.md).

---

## 12. Stack técnico completo

- **Frontend**: HTML5, CSS3, vanilla JavaScript, Vite 6, Motion One 12, Outfit font, localStorage caching
- **API**: TypeScript, Cloudflare Workers, postgres.js 3, wrangler 4
- **Base de datos**: PostgreSQL 15 (Supabase), pgBouncer, Row Level Security
- **Python tools**: plate_parser (validación de placas), pytest, ruff, mypy
- **CI/CD**: GitHub Actions, Vercel (auto-deploy desde Git), Cloudflare (wrangler deploy)
- **Testing**: pytest + pytest-cov (Python), vitest + jsdom (frontend), vitest (Worker)
