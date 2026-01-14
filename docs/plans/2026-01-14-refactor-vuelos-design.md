# Diseño: Refactorización del buscador de vuelos BCN

**Fecha:** 2026-01-14
**Estado:** Aprobado
**Enfoque:** Refactorizar código existente (Enfoque A)

## Contexto

El código actual incluye lógica para trenes que no funciona porque Amadeus Self-Service (tier gratuito) no devuelve trenes españoles. Se refactoriza para:

1. Eliminar código muerto de trenes
2. Simplificar a dos rutas independientes: MAD↔BCN y OVD↔BCN
3. Añadir legs sueltos para combinar con trenes (solo MAD↔BCN)
4. Incluir enlaces a Skyscanner y Trainline

## Usuaria y caso de uso

- **Usuaria:** Una persona específica con viajes frecuentes a Barcelona
- **Rutas fijas:** MAD↔BCN y OVD↔BCN
- **Días:** Solo entre semana (L-M, M-X, X-J, J-V)
- **Frecuencia:** Notificación semanal cada domingo

## Parámetros configurables

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `MAX_ARRIVAL_TIME` | 10:00 | Hora máxima llegada (filtro estricto) |
| `MIN_DEPARTURE_TIME` | 17:00 | Hora mínima salida (filtro estricto) |
| `RELAXED_MARGIN_MINUTES` | 60 | Margen fijo para filtros relajados |
| `SINGLE_LEG_THRESHOLD` | 45€ | Mostrar leg suelto si precio < umbral (parametrizable) |
| `WEEKS_AHEAD` | 2 | Semanas de anticipación |

Los filtros relajados se aplican automáticamente si no hay resultados con filtros estrictos:
- Llegada: `MAX_ARRIVAL_TIME + 1 hora`
- Salida: `MIN_DEPARTURE_TIME - 1 hora`

## Arquitectura

### Archivos modificados

| Archivo | Cambios |
|---------|---------|
| `config/settings.py` | Añadir `SINGLE_LEG_THRESHOLD`, `RELAXED_MARGIN_MINUTES`. Eliminar config de trenes. |
| `src/amadeus_client.py` | Fix `nonStop='true'`. Eliminar `TRAIN_CARRIERS`. Simplificar `FlightOption`. |
| `src/search.py` | Nueva estructura `RouteResult`. Búsqueda por ruta independiente. Legs sueltos solo MAD↔BCN. |
| `src/formatter.py` | Reescribir con nuevo formato + URLs. |
| `src/main.py` | Simplificar flujo (dos rutas independientes). |

### Archivo nuevo

| Archivo | Propósito |
|---------|-----------|
| `src/url_builder.py` | Generador de URLs de Skyscanner y Trainline |

### Sin cambios

- `src/telegram.py` - Funciona correctamente tal cual

## Estructuras de datos

### RouteResult

```python
@dataclass
class RouteResult:
    origin: str                         # "MAD" o "OVD"
    destination: str                    # "BCN"
    best_combo: TripOption | None       # Mejor ida+vuelta
    best_outbound: FlightOption | None  # Mejor ida suelta (si < umbral)
    best_return: FlightOption | None    # Mejor vuelta suelta (si < umbral)
    week_start: date
    relaxed_filters: bool               # True si se usaron filtros relajados
```

### FlightOption (simplificado)

```python
@dataclass
class FlightOption:
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    carrier_code: str       # "VY", "IB", "UX"
    carrier_name: str       # "Vueling", "Iberia", "Air Europa"
    flight_number: str
    date: date              # Fecha del vuelo
```

## Flujo de ejecución

```
main.py
  → search.py: search_route("MAD", "BCN", target_date) → RouteResult
  → search.py: search_route("OVD", "BCN", target_date) → RouteResult
  → formatter.py: format_telegram_message(mad_result, ovd_result) → str
  → telegram.py: send_message(message)
```

## Lógica de búsqueda

Para cada ruta (`search_route`):

1. Para cada par de días (L-M, M-X, X-J, J-V):
   - Buscar vuelos ida con `max_arrival_time`
   - Buscar vuelos vuelta con `min_departure_time`
   - Combinar mejor ida + mejor vuelta → `TripOption`

2. Si no hay resultados, repetir con filtros relajados

3. De todos los `TripOption`, el más barato → `best_combo`

4. Solo para MAD↔BCN:
   - Mejor vuelo ida con precio < `SINGLE_LEG_THRESHOLD` → `best_outbound`
   - Mejor vuelo vuelta con precio < `SINGLE_LEG_THRESHOLD` → `best_return`

## URLs

### Skyscanner

Formato ida+vuelta:
```
https://www.skyscanner.es/transporte/vuelos/{origin}/{dest}/{fecha_ida}/{fecha_vuelta}/
```

Formato solo ida:
```
https://www.skyscanner.es/transporte/vuelos/{origin}/{dest}/{fecha}/
```

### Trainline

Solo para MAD↔BCN (no hay trenes OVD↔BCN):
```
https://www.thetrainline.com/es/train-times/madrid-to-barcelona
```

## Formato del mensaje

```
✈️ VUELOS BCN - Semana del {día} {mes}

🛫 MADRID ↔ BARCELONA
   Mejor combo: {precio}€
   {día_ida} → {día_vuelta}
   MAD→BCN {hora} ({aerolínea}) {precio}€
   BCN→MAD {hora} ({aerolínea}) {precio}€
   🔗 {skyscanner_url}

   📤 Ida suelta: {precio}€ {día} {hora} ({aerolínea})
   🔗 {skyscanner_url}

   📥 Vuelta suelta: {precio}€ {día} {hora} ({aerolínea})
   🔗 {skyscanner_url}

🛫 OVIEDO ↔ BARCELONA
   Mejor combo: {precio}€
   {día_ida} → {día_vuelta}
   OVD→BCN {hora} ({aerolínea}) {precio}€
   BCN→OVD {hora} ({aerolínea}) {precio}€
   🔗 {skyscanner_url}

🚄 Compara trenes MAD↔BCN (iryo/OUIGO/AVE):
   🔗 {trainline_url}
```

**Notas:**
- Legs sueltos solo aparecen si precio < 45€
- Legs sueltos solo para MAD↔BCN (OVD no tiene trenes para combinar)
- Enlace Trainline solo al final, para MAD↔BCN

## Limitaciones conocidas

- **Trenes no incluidos en búsqueda:** Amadeus Self-Service no devuelve trenes españoles. El usuario debe comparar manualmente en Trainline.
- **Precios orientativos:** Los precios de Amadeus pueden diferir ligeramente de Skyscanner.
- **Solo vuelos directos:** No se buscan vuelos con escala.

## Consideraciones futuras (v2)

### Viajes mixtos (triangulares)
- MAD→BCN→OVD o OVD→BCN→MAD
- Requiere lógica adicional de combinación
- Legs sueltos de OVD aplicarían en este contexto

### Bot interactivo
- GitHub Actions no soporta procesos persistentes
- **Opciones recomendadas:**
  - Cloudflare Workers (gratis hasta 100k req/día) - webhooks
  - fly.io (tier gratuito) - polling
  - VPS barato (~3-5€/mes)
- Migración necesaria cuando se implemente interactividad

### Integración de trenes
- Pendiente encontrar API gratuita
- Trainline/Omio no tienen API pública
- Posible scraping (frágil)
