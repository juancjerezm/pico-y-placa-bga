# Pico y Placa Bucaramanga

**[pico-y-placa-bga.vercel.app](https://pico-y-placa-bga.vercel.app)**

Consultá si tu carro tiene restricción de Pico y Placa hoy en el Área Metropolitana de Bucaramanga (Bucaramanga, Floridablanca, Girón, Piedecuesta).

---

## Stack

| Capa | Tecnología | Host |
|------|-----------|------|
| Frontend | Vite + vanilla JS + Motion One | Vercel |
| API | TypeScript + postgres.js | Cloudflare Workers |
| DB | PostgreSQL (Supabase) | Supabase |
| Scraper | Python + BeautifulSoup | GitHub Actions |

## API

**Base**: `https://pico-y-placa-api.juanchob612.workers.dev`

### `GET /v1/restriccion`

```json
// 200 OK
{
  "municipio": "bucaramanga",
  "fecha": "2026-06-10",
  "placa_normalized": "ABC123",
  "restricted": true,
  "last_digit": 3,
  "formato_detectado": "particular",
  "rule": "weekday"
}
```

| Status | Significado |
|--------|-------------|
| 200 | Consulta exitosa |
| 400 | `bad_plate` / `bad_date` / `bad_municipio` |
| 404 | `rotation_unknown` — sin datos para esa fecha |

### `GET /v1/schedule`

Devuelve la rotación activa actual y la siguiente.

## Cómo funciona

Los dígitos del Pico y Placa rotan cada 3 meses según resolución de la DTB (Dirección de Tránsito de Bucaramanga). El scraper extrae los datos oficiales y los guarda en Supabase. La API consulta en tiempo real y el frontend muestra el resultado con una experiencia de una sola pantalla.

- **Lunes a viernes**: dígitos fijos durante el trimestre
- **Sábados**: rotan semanalmente
- **Domingos y festivos**: sin restricción

## Desarrollo

```bash
# Frontend
cd frontend && pnpm dev

# API Worker
cd worker && pnpm dev

# Scraper
cd python && uv run pytest
```

## Documentación completa

→ [DOCUMENTACION.md](DOCUMENTACION.md)
