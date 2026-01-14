# Buscador de vuelos Barcelona

Herramienta automatizada que busca las mejores opciones de vuelo/tren para ir a Barcelona 2 días consecutivos, optimizando por precio.

## Qué hace

Cada domingo a las 10:00 (hora España):

1. Busca vuelos y AVE para la semana de dentro de 2 semanas
2. Compara todas las combinaciones de días (L-M, M-X, X-J, J-V)
3. Compara rutas desde Madrid y Asturias
4. Te envía por Telegram las 3 mejores opciones

## Ejemplo de mensaje

```
✈️ VUELOS BCN - Semana del 27 ene

🥇 MEJOR OPCIÓN: 87€
   Mar 28 → Mié 29
   OVD→BCN 07:45 (Vueling) 43€
   BCN→MAD 18:30 (AVE) 44€

🥈 Segunda: 94€
   Lun 27 → Mar 28
   MAD→BCN 08:15 (AVE) 52€
   BCN→MAD 19:00 (AVE) 42€

📊 Resumen por días:
   L-M: desde 94€ | M-X: desde 87€ | X-J: desde 103€ | J-V: desde 112€

💡 Mejor día: Martes-Miércoles
```

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

## Personalización

Edita `config/settings.py` para cambiar:

- **Rutas**: Añadir/quitar aeropuertos
- **Días**: Cambiar pares de días a buscar
- **Horarios**: Ajustar hora máxima de llegada / mínima de salida
- **Anticipación**: Cambiar `WEEKS_AHEAD` para buscar más/menos semanas adelante

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

- **Amadeus API**: Gratis (500 llamadas/mes, usamos ~300)
- **GitHub Actions**: Gratis para repos públicos/privados
- **Total**: 0€
