# 🃏 Balatro AI - Asistente de Estrategia

Un asistente inteligente para el juego [Balatro](https://www.playbalatro.com/) que analiza tu mano en tiempo real mediante visión por computadora y te recomienda la mejor estrategia.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Características

- **🔍 Detección automática**: Reconoce las cartas de tu mano mediante template matching
- **📊 Análisis completo**: Evalúa todas las combinaciones posibles (1-5 cartas)
- **🎯 Recomendaciones**: Sugiere la mejor jugada para maximizar puntuación
- **🔮 Análisis de potencial**: Muestra qué manos podrías conseguir descartando
- **🔒 Detección estable**: Se bloquea al detectar 8 cartas para evitar parpadeos
- **🖥️ UI moderna**: Interfaz visual inspirada en el estilo del juego
- **📌 Modo overlay**: Ventana compacta flotante sobre el juego

## 📸 Capturas

La aplicación muestra:
- Cartas detectadas en tu mano
- Mejor jugada recomendada con puntuación esperada
- Lista de las 8 mejores jugadas posibles
- Potencial de mejora si descartas (flush, straight, etc.)
- Estadísticas: objetivo, puntos necesarios, manos y descartes restantes

## 📦 Instalación

### Requisitos
- Python 3.8+
- Windows 10/11
- Balatro corriendo en ventana

### Pasos

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/balatro-ai.git
cd balatro-ai

# Instalar dependencias
pip install -r poker_ai/requirements.txt
```

## 🚀 Uso

### Aplicación con interfaz gráfica (recomendado)

```bash
python run_ai.py
```

Selecciona la opción **1** para análisis continuo automático.

### Modo overlay compacto

```bash
python -m poker_ai.ui --overlay
```

### Desde Python

```python
from poker_ai.game_state import parse_hand, GameState, BlindInfo
from poker_ai.optimizer import StrategyOptimizer

# Crear estado de juego
hand = parse_hand("AS KS QS JS 10S 7H 3D 2C")
state = GameState(
    hand=hand,
    hands_remaining=4,
    discards_remaining=3,
    blind=BlindInfo("Big Blind", 800)
)

# Analizar
optimizer = StrategyOptimizer(state)
best = optimizer.find_best_play()

print(f"Jugar: {' '.join(str(c) for c in best.cards)}")
print(f"Tipo: {best.hand_type.display_name}")
print(f"Puntuación: {best.expected_score}")
```

## 🎴 Formato de cartas

- **Rango**: 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A
- **Palo**: S (♠ picas), H (♥ corazones), D (♦ diamantes), C (♣ tréboles)

Ejemplos: `AS` (As de picas), `KH` (Rey de corazones), `10D` (10 de diamantes)

## 📁 Estructura del proyecto

```
balatro-ai/
├── run_ai.py              # Punto de entrada principal (CLI)
├── poker_ai/
│   ├── __init__.py
│   ├── main.py            # Orquestador y utilidades
│   ├── game_state.py      # Modelo de datos (Card, GameState, HandType)
│   ├── optimizer.py       # Motor de estrategia y análisis
│   ├── screen_capture.py  # Captura de ventana (Win32)
│   ├── vision.py          # Detección de cartas (OpenCV)
│   ├── ui.py              # Interfaz gráfica (Tkinter)
│   ├── requirements.txt   # Dependencias
│   └── templates/         # 52 templates de cartas (PNG)
└── backup_beta_v1/        # Backup de versión anterior
```

## ⚙️ Configuración

La detección está calibrada para una resolución específica. Si no detecta bien las cartas:

1. Ajusta `HAND_REGION` en `vision.py` (coordenadas de la zona de cartas)
2. Ajusta `scale` en `TemplateCardDetector` (tamaño de templates)
3. Ajusta `threshold` (sensibilidad, default 0.45)

## 🔧 Parámetros de detección

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `scale` | 0.75 | Escala de templates |
| `threshold` | 0.45 | Confianza mínima (0-1) |
| `nms_distance` | 70 | Distancia NMS en píxeles |
| `HAND_REGION` | (200, 480, 1200, 280) | Región de búsqueda (x, y, w, h) |

## 🚧 Limitaciones conocidas

- Solo funciona en Windows
- Requiere calibración para diferentes resoluciones
- No detecta jokers automáticamente (valores por defecto)
- No lee el objetivo/manos/descartes de la pantalla
- Los templates deben coincidir con el estilo visual del juego

## 🛠️ Desarrollo futuro

- [ ] Detección multi-escala para diferentes resoluciones
- [ ] OCR para leer objetivo y recursos de la pantalla
- [ ] Detección de cartas seleccionadas (elevadas)
- [ ] Base de datos completa de jokers
- [ ] Tracking del mazo para probabilidades exactas
- [ ] Soporte para Linux/macOS

## 📄 Licencia

MIT License - Libre para uso personal y comercial.

## 🙏 Créditos

- [Balatro](https://www.playbalatro.com/) - El increíble juego de LocalThunk
- OpenCV - Visión por computadora
- Tkinter - Interfaz gráfica
