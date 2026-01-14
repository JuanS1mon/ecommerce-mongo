# Ecommerce ORM API

Una aplicación FastAPI completa para un sistema de ecommerce con autenticación, gestión de productos, carritos de compra y pagos con MercadoPago.

## Características

- 🚀 **FastAPI** - Framework web moderno y rápido
- 🍃 **MongoDB** con **Beanie** - Base de datos NoSQL con ODM (Dual Database Architecture)
- 🔐 **Autenticación JWT** - Sistema seguro de autenticación con validación de vencimientos
- 🔄 **Sincronización de Usuarios** - Sistema automático de sincronización entre bases de datos
- 💳 **MercadoPago** - Integración de pagos
- 📧 **Sistema de correos** - Envío de emails
- 🔍 **Azure Search** - Búsqueda avanzada de productos
- 📱 **API RESTful** - Endpoints bien documentados
- 🌐 **API de Validación Externa** - Integración con aplicaciones externas

## 🗄️ Arquitectura de Bases de Datos

Este proyecto utiliza **DOS bases de datos DIFERENTES**:

1. **Base de Datos Local (App)** - `db_ecomerce` (**Azure SQL Server**)
   - Base de datos principal de la aplicación
   - Almacena productos, pedidos, carritos, etc.
   - Usuarios admin sincronizados
   - Motor: Microsoft SQL Server en Azure

2. **Base de Datos Externa (Remota)** - `db_sysne` (**MongoDB Atlas**)
   - Base de datos centralizada de usuarios admin
   - Fuente de verdad para proyectos y vinculaciones
   - Sistema multi-aplicación
   - Motor: MongoDB en Atlas

📖 **Ver documentación completa:** [ARQUITECTURA_BASES_DATOS.md](./ARQUITECTURA_BASES_DATOS.md)

## Requisitos

- Python 3.11+
- Azure Cosmos DB con API de MongoDB (ecommerce-db)
- Acceso a la base de datos externa MongoDB Atlas `db_sysne`
- Cuenta de MercadoPago (opcional)
- Azure Search (opcional)

## Instalación

1. **Clona el repositorio:**
   ```bash
   git clone <url-del-repositorio>
   cd sql_app_Ecomerce_orm
   ```

2. **Crea un entorno virtual:**
   ```bash
   python -m venv venv
   ```

3. **Activa el entorno virtual:**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
   O usando el `Makefile`:
   ```bash
   make install
   ```

   (Se normalizó `requirements.txt` para evitar duplicados y dependencias redundantes.)
5. **Configura las variables de entorno:**
   Crea un archivo `.env` en la raíz del proyecto con:
   ```env
   # Base de datos
   MONGODB_URL=mongodb://localhost:27017/ecommerce

   # JWT
   SECRET_KEY=tu_clave_secreta_aqui
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30

   # MercadoPago
   MERCADOPAGO_ACCESS_TOKEN=tu_token_de_mercadopago

   # Correo
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=tu_email@gmail.com
   SMTP_PASSWORD=tu_password_app

   # Azure Search (opcional)
   AZURE_SEARCH_ENDPOINT=https://tu-search.search.windows.net
   AZURE_SEARCH_KEY=tu_clave_de_busqueda
   AZURE_SEARCH_INDEX=productos
   ```

   ## Google OAuth (Iniciar sesión con Google)

   1. Crea credenciales en Google Cloud Console (OAuth Client ID) para una aplicación web.
   2. Añade el redirect URI apuntando a tu backend, por ejemplo:

   ```text
   http://localhost:8000/auth/google/callback
   ```

   3. Añade las siguientes variables en tu `.env`:

   ```env
   GOOGLE_CLIENT_ID=tu_client_id
   GOOGLE_CLIENT_SECRET=tu_client_secret
   # Opcional: FRONTEND_URL si necesitas redirigir al frontend
   ```

   4. Reinicia el servidor y en las páginas de login/registro aparecerá el botón "Continuar con Google" si la configuración es correcta.

## Ejecución

1. **Inicia el servidor:**
   ```bash
   python main.py
   ```

2. **Accede a la aplicación:**
   - API Docs: http://localhost:8000/docs
   - Admin Panel: http://localhost:8000/admin
   - Frontend: http://localhost:8000

## Estructura del Proyecto

```
├── main.py                 # Archivo principal de la aplicación
├── config.py              # Configuraciones generales
├── app_settings.py        # Configuración de CORS y middlewares
├── logging_config_new.py  # Configuración de logging
├── requirements.txt       # Dependencias del proyecto
├── alembic/               # Migraciones de base de datos
├── routers/               # Endpoints de la API
│   ├── auth.py
│   ├── usuarios.py
│   ├── ecommerce_public.py
│   └── ...
├── db/                    # Configuración de base de datos
├── middleware/            # Middlewares personalizados
├── security/              # Utilidades de seguridad
├── Services/              # Servicios de negocio
├── static/                # Archivos estáticos
├── templates/             # Plantillas HTML
└── utils/                 # Utilidades generales
```

## API Endpoints Principales

### Autenticación
- `POST /ecomerce/auth/register` - Registro de usuarios
- `POST /ecomerce/auth/login` - Inicio de sesión
- `POST /ecomerce/auth/logout` - Cierre de sesión

### Productos
- `GET /ecomerce/api/productos/publicos` - Lista de productos públicos
- `GET /ecomerce/api/productos/{id}` - Detalle de producto

- `POST /ecomerce/checkout/` - Procesa checkout para métodos 'efectivo' y 'presupuesto' (requiere Authorization). Retorna `order_id`.
- `POST /ecomerce/checkout/` (con `payment_method=mercadopago`) - Crea preferencia MercadoPago y retorna `preference_id` y `order_id`.
- `POST /ecomerce/checkout/webhook/mercadopago` - Webhook para notificaciones de MercadoPago (configurar `MERCADOPAGO_NOTIFICATION_URL`).

Environment variables required for payments/email:
- `ADMIN_EMAIL` (email del administrador)
- `COMPANY_PHONE` (teléfono de contacto de la empresa)
- `MERCADOPAGO_PUBLIC_KEY`, `MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_ENVIRONMENT`
- Email: `SMTP_SERVER`, `USERNAME_EMAIL`, `PASSWORD_EMAIL`, `MAIL_FROM`
- `GET /ecomerce/api/categorias/publicas` - Categorías disponibles

### Carrito de Compras
- `POST /ecomerce/carritos/` - Crear carrito
- `POST /ecomerce/carrito_items/` - Agregar producto al carrito
- `GET /ecomerce/carritos/activo/{user_id}` - Carrito activo del usuario

### Checkout
- `POST /ecomerce/checkout/` - Procesar pago con MercadoPago
- `POST /ecomerce/checkout/webhook/mercadopago` - Webhook de MercadoPago

## Desarrollo

### Ejecutar en modo desarrollo con recarga automática:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Ejecutar en desarrollo con Docker (Mongo + app) ✅
1. Copia `.env.example` a `.env` y ajusta valores.
2. Levanta servicios:
```bash
docker compose -f docker-compose.dev.yml up --build -d
```
3. Accede a la app en http://localhost:8001
4. Para detener:
```bash
docker compose -f docker-compose.dev.yml down
```

### Ejecutar tests con Mongo corriendo
Asegúrate de que Mongo esté en `mongodb://localhost:27017` o que `MONGO_URL` apunte al contenedor. Luego ejecuta:
```bash
pytest
```

### Ejecutar pruebas:
```bash
pytest
```

### Generar documentación:
La documentación automática está disponible en `/docs` cuando el servidor está ejecutándose.

## Despliegue

### Usando Docker:
```bash
docker build -t ecommerce-api .
docker run -p 8000:8000 ecommerce-api
```

### Variables de Entorno para Producción:
```env
ENVIRONMENT=production
DEBUG=False
FRONTEND_URL=https://tu-dominio.com
```

## Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Soporte

Para soporte técnico o preguntas, por favor abre un issue en el repositorio.