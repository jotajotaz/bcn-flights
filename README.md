# Buscador de vuelos Barcelona

Herramienta automatizada que busca las mejores opciones de vuelo para ir a Barcelona 2 días consecutivos, optimizando por precio.

## Qué hace

Cada domingo a las 10:00 (hora España):

1. Busca vuelos para la semana de dentro de 2 semanas
2. Compara todas las combinaciones de días (L-M, M-X, X-J, J-V)
3. Compara rutas desde Madrid (MAD) y Oviedo (OVD)
4. Te envía por Telegram las mejores opciones con enlaces para reservar

## Fuentes de datos

| Transporte | Fuente | Notas |
|------------|--------|-------|
| Vuelos | Amadeus API (gratis) | Iberia, Vueling, Air Europa, etc. |
| Trenes | No disponible | Amadeus Rail requiere plan Enterprise (de pago) |

Para trenes (AVE, iryo, OUIGO, Avlo), el mensaje incluye un enlace a Trainline donde el usuario puede comparar manualmente.

## Ejemplo de mensaje

```
✈️ VUELOS BCN - Semana del 27 ene

🛫 MADRID ↔ BARCELONA
   Mejor combo: 122€
   Mar 28 → Mié 29
   MAD→BCN 07:30 (Air Europa) 50€
   BCN→MAD 19:10 (Vueling) 72€
   🔗 skyscanner.es/...

   📤 Ida suelta: 42€ Mar 28 07:30 (Air Europa)
   🔗 skyscanner.es/...

🛫 OVIEDO ↔ BARCELONA
   Mejor combo: 156€
   Lun 27 → Mar 28
   OVD→BCN 08:15 (Vueling) 78€
   BCN→OVD 18:45 (Vueling) 78€
   🔗 skyscanner.es/...

🚄 Compara trenes (iryo/OUIGO/AVE):
   trainline.com/train-times/madrid-to-barcelona
```

### Lógica del mensaje

- **Mejor combo**: La combinación ida+vuelta más barata de la semana para cada ruta
- **Ida/vuelta suelta**: Solo se muestra si el precio es < umbral (default: 45€), útil para combinar con tren
- **Enlaces**: Skyscanner para vuelos, Trainline para trenes

## Parámetros configurables

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `MAX_ARRIVAL_TIME` | 10:00 | Hora máxima de llegada (vuelos de ida) |
| `MIN_DEPARTURE_TIME` | 17:00 | Hora mínima de salida (vuelos de vuelta) |
| `SINGLE_LEG_THRESHOLD` | 45€ | Solo mostrar vuelo suelto si cuesta menos que esto |
| `WEEKS_AHEAD` | 2 | Semanas de anticipación para buscar |

## Configuración

### 1. Obtener API Key de Amadeus (gratis)

1. Ve a https://developers.amadeus.com
2. Crea una cuenta
3. Crea una "App" en el dashboard
4. Copia el **API Key** y **API Secret**

### 2. Crear bot de Telegram

1. Abre Telegram y busca `@BotFather`
2. Envía `/newbot`
3. Dale un nombre y username
4. Copia el **BOT_TOKEN** que te devuelve

Para obtener tu **CHAT_ID**:
1. Inicia una conversación con tu bot (envíale cualquier mensaje)
2. Visita: `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
3. Busca el campo `"chat":{"id":123456789}` - ese número es tu CHAT_ID

### 3. Configurar secrets en GitHub

Ve a tu repo → Settings → Secrets and variables → Actions → New repository secret

Añade estos 4 secrets:

| Nombre | Valor |
|--------|-------|
| `AMADEUS_API_KEY` | Tu API Key de Amadeus |
| `AMADEUS_API_SECRET` | Tu API Secret de Amadeus |
| `TELEGRAM_BOT_TOKEN` | Token de tu bot de Telegram |
| `TELEGRAM_CHAT_ID` | Tu Chat ID |

### 4. Activar GitHub Actions

El workflow ya está configurado para correr cada domingo a las 10:00.

Para probarlo manualmente:
1. Ve a Actions → "Búsqueda semanal de vuelos"
2. Click en "Run workflow"

## Ejecución local (opcional)

```bash
# Clonar repo
git clone https://github.com/hormigo69/bcn-flights.git
cd bcn-flights

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Edita .env con tus credenciales

# Ejecutar
python src/main.py
```

## Estructura del proyecto

```
bcn-flights/
├── src/
│   ├── main.py              # Punto de entrada
│   ├── amadeus_client.py    # Consultas a Amadeus API
│   ├── search.py            # Lógica de búsqueda
│   ├── formatter.py         # Formato del mensaje
│   └── telegram.py          # Envío a Telegram
├── config/
│   └── settings.py          # Configuración
├── logs/                    # Logs de ejecuciones
├── .github/workflows/
│   └── weekly.yml           # GitHub Action
└── requirements.txt
```

## Costes

- **Amadeus API**: Gratis (500 llamadas/mes, usamos ~50)
- **GitHub Actions**: Gratis para repos públicos/privados
- **Total**: 0€

## Limitaciones conocidas

- **Trenes no incluidos**: Amadeus Self-Service no incluye trenes españoles. Para comparar con AVE/iryo/OUIGO, usar el enlace a Trainline.
- **Precios pueden variar**: Los precios de Amadeus son orientativos. El enlace a Skyscanner puede mostrar precios ligeramente diferentes.
- **Solo vuelos directos**: No se buscan vuelos con escala.

## Casos de uso futuros (v2)

- [ ] Viajes mixtos: MAD→BCN→OVD o OVD→BCN→MAD
- [ ] Interactividad: Bot de Telegram que responda a comandos
- [ ] Integración de trenes si se encuentra API gratuita
