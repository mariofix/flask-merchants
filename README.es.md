# flask-merchants

Extensión Flask/Quart para el SDK de pagos [merchants](https://github.com/mariofix/merchnts-cp) (hosted-checkout).

## Características

- Clase de extensión `FlaskMerchants` con soporte completo para `init_app` – pasa `db`, `models`, `provider`, `providers` y `admin` al constructor **o** de forma diferida a `init_app` (compatible con el patrón application-factory)
- Blueprint con rutas para checkout, páginas de aterrizaje de éxito/cancelación, estado del pago, webhooks y listado de proveedores
- Soporte para múltiples proveedores de pago – registra proveedores por nombre a través del registro del SDK `merchants` y selecciona uno en cada petición de checkout
- Usa `DummyProvider` por defecto – no se necesitan credenciales para desarrollo local
- Vistas opcionales de Flask-Admin (en `flask_merchants.contrib.admin`) para listar y actualizar estados de pago
- **Integración automática con Flask-Admin** – pasa `admin=` a `FlaskMerchants` para registrar automáticamente `PaymentView` y `ProvidersView` bajo la categoría *Merchants* con una sola línea
- Vista opcional de Flask-Admin respaldada por SQLAlchemy (`flask_merchants.contrib.sqla`) con acciones masivas de reembolso/cancelación/sincronización
- Soporte asíncrono con Quart – el blueprint asíncrono se selecciona automáticamente al detectar una aplicación `quart.Quart`

## Instalación

```bash
pip install flask-merchants           # núcleo
pip install "flask-merchants[admin]"  # con soporte para Flask-Admin
pip install "flask-merchants[db]"     # con SQLAlchemy + Flask-Admin
pip install "flask-merchants[quart]"  # con soporte asíncrono (Quart)
```

## Inicio rápido

```python
from flask import Flask
from flask_merchants import FlaskMerchants

app = Flask(__name__)
ext = FlaskMerchants(app)  # usa DummyProvider por defecto
```

### Quart (asíncrono)

`FlaskMerchants` detecta automáticamente una aplicación `quart.Quart` y registra
un blueprint asíncrono:

```python
from quart import Quart
from flask_merchants import FlaskMerchants

app = Quart(__name__)
ext = FlaskMerchants(app)   # blueprint asíncrono seleccionado automáticamente
```

Requiere el extra `quart`:

```bash
pip install "flask-merchants[quart]"
```

### Rutas disponibles (prefijo por defecto `/merchants`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/POST | `/merchants/checkout` | Crear una sesión de pago |
| GET | `/merchants/providers` | Listar proveedores de pago disponibles |
| GET | `/merchants/success` | Página de aterrizaje de pago exitoso |
| GET | `/merchants/cancel` | Página de aterrizaje de pago cancelado |
| GET | `/merchants/status/<payment_id>` | Estado del pago en tiempo real |
| POST | `/merchants/webhook` | Recibir eventos de webhook |

### Configuración

| Clave | Valor por defecto | Descripción |
|-------|-------------------|-------------|
| `MERCHANTS_URL_PREFIX` | `/merchants` | Prefijo de URL para el blueprint |
| `MERCHANTS_WEBHOOK_SECRET` | `None` | Secreto HMAC-SHA256 para verificación de webhooks |

### Patrón application-factory

Todos los parámetros de configuración (`db`, `models`, `provider`, `providers`, `admin`)
pueden pasarse al constructor `FlaskMerchants()` **o** a `init_app()` de forma
diferida. Ambos estilos son equivalentes:

```python
# Estilo A – todo al momento de construcción
from flask import Flask
from flask_merchants import FlaskMerchants

app = Flask(__name__)
ext = FlaskMerchants(app, db=db, models=[Pagos])
```

```python
# Estilo B – configuración diferida a init_app (patrón application-factory)
# extensions.py
from flask_merchants import FlaskMerchants
merchants_ext = FlaskMerchants()

# app_factory.py
def create_app():
    app = Flask(__name__)
    db = SQLAlchemy(model_class=Base)
    merchants_ext.init_app(app, db=db, models=[Pagos], provider=MiProveedor())
    return app
```

Los parámetros proporcionados a `init_app` sobreescriben cualquier valor
establecido previamente en `__init__`.

### Integración con Flask-Admin (automática)

Pasa una instancia de `flask_admin.Admin` a `FlaskMerchants` y ambas vistas de
administración se registran automáticamente bajo la categoría **Merchants** – sin
configuración manual:

```python
from flask import Flask
from flask_admin import Admin
from flask_merchants import FlaskMerchants

app = Flask(__name__)
admin = Admin(app, name="Mi Tienda")
ext = FlaskMerchants(app, admin=admin)
# Listo — PaymentView y ProvidersView registradas bajo "Merchants"
```

También funciona con el patrón application-factory:

```python
ext = FlaskMerchants()
ext.init_app(app, admin=admin)
```

Se registran dos vistas automáticamente:

| Vista | URL | Descripción |
|-------|-----|-------------|
| **Payments** | `/admin/merchants_payments/` | Listar, actualizar, reembolsar, cancelar y sincronizar pagos |
| **Providers** | `/admin/merchants_providers/` | Vista de depuración de todos los proveedores registrados |

La vista **Providers** muestra la siguiente información por proveedor:

| Columna | Descripción |
|---------|-------------|
| Provider Key | Clave única del proveedor (ej. `dummy`, `stripe`) |
| Base URL | URL base de la API del proveedor |
| Auth Type | Clase de estrategia de autenticación (`None`, `ApiKeyAuth`, `TokenAuth`) |
| Auth Header | Cabecera HTTP por la que se envía la credencial |
| Auth Value | Credencial enmascarada – primeros 5 chars + `…` + último char (ej. `sk_te…0`) |
| Transport | Clase de capa de transporte (ej. `RequestsTransport`) |
| Payments | Número de pagos almacenados enrutados a este proveedor |

También puedes registrar las vistas manualmente:

```python
from flask_merchants.contrib.admin import register_admin_views

register_admin_views(admin, ext)
```

O agregar vistas individuales directamente:

```python
from flask_merchants.contrib.admin import PaymentView, ProvidersView

admin.add_view(PaymentView(ext, name="Pagos", endpoint="payments", category="Merchants"))
admin.add_view(ProvidersView(ext, name="Proveedores", endpoint="providers", category="Merchants"))
```

### Selección de proveedor de pago

Registra uno o más proveedores a través del registro del SDK `merchants` y luego
selecciona uno por petición de checkout usando el campo `provider`:

```python
import merchants
from merchants.providers.dummy import DummyProvider

merchants.register_provider(DummyProvider())
# merchants.register_provider(StripeProvider(api_key="sk_test_..."))

app = Flask(__name__)
ext = FlaskMerchants(app)
```

También puedes pasar proveedores directamente a través de la extensión:

```python
ext = FlaskMerchants(app, provider=DummyProvider())
# o una lista:
ext = FlaskMerchants(app, providers=[DummyProvider(), StripeProvider(api_key="sk_test_...")])
```

Lista los proveedores disponibles en tiempo de ejecución:

```
GET /merchants/providers
→ {"providers": ["dummy", "stripe"]}
```

Selecciona un proveedor al hacer checkout:

```
POST /merchants/checkout
{"amount": "19.99", "currency": "USD", "provider": "stripe"}
```

Si se omite `provider`, se usa el primero registrado. Una clave de proveedor
desconocida devuelve HTTP 400.

### Usa tu propio modelo

Instala el extra `db` y mezcla `PaymentMixin` en tu propio modelo SQLAlchemy.
Pásalo mediante `models=` a `FlaskMerchants`:

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer
from flask_merchants import FlaskMerchants
from flask_merchants.models import PaymentMixin

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Pagos(PaymentMixin, db.Model):
    __tablename__ = "pagos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # agrega tus propias columnas aquí …

app = Flask(__name__)
ext = FlaskMerchants(app, db=db, models=[Pagos])
```

### Iniciar pago sobre un registro persistido

Cuando tu objeto de dominio ya está guardado (por ejemplo, una orden creada
antes del checkout), llama a `start_payment()` sobre la instancia:

```python
with app.app_context():
    pago = Pagos(
        merchants_id="order-42",
        transaction_id="pending-order-42",
        provider="dummy",
        amount="19.99",
        currency="USD",
        state="pending",
    )
    db.session.add(pago)
    db.session.commit()

    redirect_url = pago.start_payment(
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
        extra_args={"reference": "order-42"},
    )
```

`start_payment()` valida que el registro esté persistido y en `state="pending"`,
guarda payloads de request/response para auditoría, actualiza los datos de la
transacción del proveedor, hace `commit` y retorna `redirect_url`.

### Múltiples modelos de pago en la misma aplicación

Una **única** instancia de `FlaskMerchants` puede gestionar cualquier número de
modelos a la vez usando `models=`:

```python
class Pagos(PaymentMixin, db.Model):
    __tablename__ = "pagos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

class Paiements(PaymentMixin, db.Model):
    __tablename__ = "paiements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

ext = FlaskMerchants(app, db=db, models=[Pagos, Paiements])

# Dirigir un checkout a un modelo específico:
session = ext.client.payments.create_checkout(...)
ext.save_session(session, model_class=Paiements)

# get_session / update_state / refund_session / cancel_session buscan en
# todos los modelos registrados automáticamente.

# all_sessions() devuelve todos los registros de todos los modelos combinados.
# all_sessions(model_class=Pagos) filtra a un único modelo.
```

Agrega una vista de Flask-Admin separada por modelo, todas respaldadas por el mismo `ext`:

```python
from flask_merchants.contrib.sqla import PaymentModelView
from flask_admin import Admin

admin = Admin(app)
admin.add_view(PaymentModelView(Pagos,     db.session, ext=ext, name="Pagos",     endpoint="pagos"))
admin.add_view(PaymentModelView(Paiements, db.session, ext=ext, name="Paiements", endpoint="paiements"))
```

### Flask-Admin (legado / manual)

Para un control más fino, o cuando se usa la vista respaldada por SQLAlchemy,
puedes registrar vistas individuales manualmente:

```python
from flask_admin import Admin
from flask_merchants.contrib.admin import PaymentView

admin = Admin(app, name="Mi Tienda")
admin.add_view(PaymentView(ext, name="Pagos", endpoint="payments"))
```

Consulta la sección [Integración con Flask-Admin (automática)](#integración-con-flask-admin-automática)
para el enfoque recomendado con una sola línea.

## Ejemplos

Consulta el directorio `examples/`:

- `examples/basic_app.py` – uso básico con DummyProvider
- `examples/admin_app.py` – uso con Flask-Admin (almacenamiento en memoria)
- `examples/sqla_app.py` – pagos respaldados por SQLAlchemy con Flask-Admin
- `examples/pagos_app.py` – **modelo propio** (`Pagos`) con Flask-Admin
- `examples/multi_model_app.py` – **múltiples modelos** (`Pagos` + `Paiements`) con un solo `ext`
- `examples/quart_app.py` – uso asíncrono con Quart y DummyProvider

## Tests

```bash
pip install "flask-merchants[dev]"
pytest
```

## Licencia

MIT
