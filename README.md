# FinanceCalc

Calculadora financiera TVM (Time Value of Money) moderna — misma funcionalidad que una calculadora financiera tradicional (PV, PMT, FV, RATE, N, amortización), con una interfaz rediseñada.

## Stack

- **Backend:** Python (Flask). Toda la matemática financiera vive en [`tvm.py`](tvm.py) — sin librerías externas de cálculo.
- **Frontend:** HTML5 + CSS3 + JavaScript vanilla. Tema oscuro/claro, glassmorphism, animaciones.

## Funcionalidades

- Resolver **PV, PMT, FV, RATE o N** dado el resto de las variables (ecuación TVM estándar, igual que una HP12C / BA II Plus).
- Tasa **Nominal** o **Efectiva**, con capitalización Anual / Semestral / Trimestral / Mensual / Quincenal / Bisemanal / Semanal / Diaria.
- Modo de pago **Fin de período** (anualidad ordinaria) o **Inicio de período** (anualidad anticipada).
- **Tabla de amortización** completa (interés, capital, saldo por período) con resumen y exportación a CSV.
- **Historial** automático de cálculos y **escenarios guardados** con nombre (persistidos en el navegador).
- Selector de **decimales** (2 a 5).
- Botón de **ejemplo** precargado y modal de **instrucciones**.

## Uso

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abrir [http://localhost:5000](http://localhost:5000).

## Convención de signos

El dinero que sale de tu bolsillo (pagos de un préstamo, una inversión que hacés) es **negativo**. El dinero que recibís (el monto de un préstamo otorgado, un retiro) es **positivo**.

## Estructura

```
app.py              Servidor Flask y endpoints de la API
tvm.py               Motor de cálculo financiero (PV/PMT/FV/RATE/N + amortización)
templates/index.html Interfaz
static/css/style.css Estilos
static/js/app.js     Lógica de interacción con la API
```
