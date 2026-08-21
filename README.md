# FinanceCalc

Ofir Tal note 

Calculadora financiera TVM (Time Value of Money) moderna — misma funcionalidad que una calculadora financiera tradicional (PV, PMT, FV, RATE, N, amortización), con una interfaz rediseñada, login con Google y guardado permanente de historial.


hi roberto

## Stack

- **Backend:** Python (Flask + SQLAlchemy). Toda la matemática financiera vive en [`tvm.py`](tvm.py) — sin librerías externas de cálculo.
- **Auth:** Google OAuth 2.0 vía [Authlib](https://authlib.org/) — sin contraseñas propias.
- **Base de datos:** SQLite (`instance/financecalc.db`), creada automáticamente al arrancar.
- **Frontend:** HTML5 + CSS3 + JavaScript vanilla. Tema oscuro/claro, glassmorphism, animaciones.

## Funcionalidades

- **Página de inicio** con login/registro vía Google.
- Resolver **PV, PMT, FV, RATE o N** dado el resto de las variables (ecuación TVM estándar, igual que una HP12C / BA II Plus).
- Tasa **Nominal** o **Efectiva**, con capitalización Anual / Semestral / Trimestral / Mensual / Quincenal / Bisemanal / Semanal / Diaria.
- Modo de pago **Fin de período** (anualidad ordinaria) o **Inicio de período** (anualidad anticipada).
- **Tabla de amortización** completa (interés, capital, saldo por período) con resumen y exportación a CSV.
- **Historial automático** de cada cálculo resuelto y **escenarios guardados** con nombre — persistidos en la base de datos por usuario cuando hay sesión iniciada; en `localStorage` del navegador cuando se usa sin cuenta.
- Selector de **decimales** (2 a 5), botón de **ejemplo** precargado y modal de **instrucciones**.
- **Panel de administración** (`/admin/users`) con la lista de todos los usuarios registrados — restringido a los emails en `ADMIN_EMAILS`.

## Registro / Login

El signup se hace exclusivamente con **Google** (no hay contraseñas propias). Al registrarse por primera vez, se pide:

- **Teléfono** (obligatorio).
- Aceptar los **Términos y Condiciones** y la **Política de Privacidad**, que incluyen la autorización para usar el email en campañas de marketing (checkbox obligatorio, único paso de consentimiento).

## Configuración

### 1. Variables de entorno

```bash
cp .env.example .env
```

Completá `SECRET_KEY` (generala con `python -c "import secrets; print(secrets.token_hex(32))"`) y `ADMIN_EMAILS` (tu email, separado por coma si son varios).

### 2. Credenciales de Google OAuth

1. Entrá a [Google Cloud Console](https://console.cloud.google.com/) → creá un proyecto (o usá uno existente).
2. **APIs y servicios → Pantalla de consentimiento OAuth**: configurala en modo "Externo", completá nombre de la app y email de soporte.
3. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**.
   - Tipo de aplicación: **Aplicación web**.
   - **Orígenes autorizados de JavaScript**: `http://localhost:5000`
   - **URI de redirección autorizados**: `http://localhost:5000/login/google/callback`
4. Copiá el **Client ID** y **Client Secret** generados a tu `.env`:
   ```
   GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=xxxxxxxx
   ```
5. Si desplegás en un dominio real, agregá también esa URL en los pasos 3 (origen + redirect URI con `https://tu-dominio.com/login/google/callback`).

### 3. Instalar y correr

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abrir [http://localhost:5000](http://localhost:5000). La base de datos SQLite se crea sola en `instance/financecalc.db` la primera vez.

> Sin `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` configurados, la calculadora funciona igual en modo invitado (historial en el navegador); solo el botón "Continuar con Google" no va a funcionar hasta que completes ese paso.

## Convención de signos

El dinero que sale de tu bolsillo (pagos de un préstamo, una inversión que hacés) es **negativo**. El dinero que recibís (el monto de un préstamo otorgado, un retiro) es **positivo**.

## Estructura

```
app.py                  Servidor Flask, rutas y endpoints de la API
auth.py                 Login/registro con Google OAuth
models.py                Modelos de base de datos (User, CalculationHistory, SavedScenario)
tvm.py                   Motor de cálculo financiero (PV/PMT/FV/RATE/N + amortización)
templates/landing.html   Página de inicio
templates/register.html  Completar registro (teléfono + términos)
templates/index.html     Calculadora
templates/terms.html     Términos y Condiciones
templates/privacy.html   Política de Privacidad
templates/admin_users.html  Panel de usuarios registrados
static/css/               Estilos
static/js/app.js          Lógica de interacción con la API
```

## Notas de producción

- Los textos de Términos y Privacidad son un modelo de referencia — hacelos revisar por un abogado antes de operar con usuarios reales.
- `python app.py` usa el servidor de desarrollo de Flask. Para producción, serví la app con un WSGI real (gunicorn/waitress) detrás de un proxy HTTPS.
- La cookie de sesión depende de `SECRET_KEY`: usá un valor largo y secreto distinto en cada entorno.
