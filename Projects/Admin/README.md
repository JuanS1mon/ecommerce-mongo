# Panel de Administración del Ecommerce

Panel administrativo completo para gestionar el ecommerce, separado de la aplicación principal.

## 📋 Características

### 🎛️ Dashboard Principal
- Estadísticas en tiempo real:
  - Total de productos activos/inactivos
  - Total de pedidos por estado
  - Ventas totales y del mes
  - Usuarios activos
  - Carritos activos y abandonados
- Productos más vendidos (Top 5)
- Pedidos recientes (últimos 10)

### 📦 Gestión de Productos
- **Listar productos** con filtros y búsqueda
- **Crear productos** nuevos con:
  - Código, nombre, descripción
  - Categoría, precio
  - Imagen URL
  - Estado activo/inactivo
- **Editar productos** existentes
- **Activar/Desactivar** productos
- Ver variantes de productos

### 📋 Gestión de Pedidos
- **Listar pedidos** con filtros:
  - Por estado (pendiente, procesando, enviado, entregado, cancelado)
  - Por rango de fechas
  - Por usuario
- **Ver detalles completos** de cada pedido:
  - Items del pedido
  - Información del cliente
  - Método de pago
- **Cambiar estado** de pedidos
- **Estadísticas** de pedidos por estado

### 💼 Gestión de Presupuestos
- **Listar presupuestos** con filtros
- **Ver detalles** de cada presupuesto
- **Aprobar/Rechazar** presupuestos
- **Convertir a pedido** (funcionalidad base)

### 🛒 Monitoreo de Carritos
- **Ver todos los carritos** activos
- **Identificar carritos abandonados** (más de 7 días)
- **Ver detalles** de cada carrito:
  - Items en el carrito
  - Usuario asociado
  - Días de inactividad
- **Estadísticas** de carritos:
  - Tasa de abandono
  - Total de carritos completados

### 👥 Administración de Usuarios
- **Gestión de usuarios del sistema**:
  - Listar con filtros y búsqueda
  - Ver detalles y roles
  - Activar/Desactivar cuentas
  - Asignar/Modificar roles
- **Gestión de usuarios del ecommerce**:
  - Listar clientes
  - Ver información de contacto
  - Activar/Desactivar cuentas
- **Gestión de roles**

## 🔐 Autenticación y Seguridad

### Sistema de Autenticación
- Usa la tabla `Usuarios` existente del sistema
- Validación mediante JWT (reutiliza el sistema actual)
- Middleware `require_admin` que verifica:
  - Usuario autenticado
  - Usuario activo
  - Rol de "admin" o "administrador"

### Protección de Rutas
Todas las rutas del panel están protegidas:
```python
from Projects.Admin.middleware.admin_auth import require_admin

@router.get("/admin/dashboard")
async def dashboard(admin_user: Usuarios = Depends(require_admin)):
    # Solo usuarios con rol admin pueden acceder
    ...
```

## 🚀 Acceso al Panel

### URL Principal
```
http://localhost:8000/admin
```

### Flujo de Acceso
1. Usuario debe estar autenticado con JWT
2. El sistema verifica que tenga rol "admin"
3. Accede al dashboard con estadísticas

### Rutas Disponibles
```
GET  /admin                          → Redirige a /admin/dashboard
GET  /admin/dashboard                → Dashboard principal
GET  /admin/api/dashboard/stats     → API de estadísticas

GET  /admin/productos                → Vista de productos
GET  /admin/api/productos/list      → API lista de productos
POST /admin/api/productos/create    → API crear producto
PUT  /admin/api/productos/{id}      → API actualizar producto
DELETE /admin/api/productos/{id}    → API desactivar producto

GET  /admin/pedidos                  → Vista de pedidos
GET  /admin/api/pedidos/list        → API lista de pedidos
GET  /admin/api/pedidos/{id}        → API detalles de pedido
PUT  /admin/api/pedidos/{id}/estado → API cambiar estado

GET  /admin/presupuestos             → Vista de presupuestos
GET  /admin/api/presupuestos/list   → API lista de presupuestos
PUT  /admin/api/presupuestos/{id}/aprobar → API aprobar
PUT  /admin/api/presupuestos/{id}/rechazar → API rechazar

GET  /admin/carritos                 → Vista de carritos
GET  /admin/api/carritos/list       → API lista de carritos
GET  /admin/api/carritos/{id}       → API detalles de carrito

GET  /admin/usuarios                 → Vista de usuarios
GET  /admin/api/usuarios/sistema/list → API usuarios sistema
GET  /admin/api/usuarios/ecommerce/list → API usuarios ecommerce
PUT  /admin/api/usuarios/sistema/{id}/toggle-active → Activar/Desactivar
PUT  /admin/api/usuarios/sistema/{id}/roles → Actualizar roles
```

## 📂 Estructura del Proyecto

```
Projects/Admin/
├── __init__.py
├── routes_config.py              # Configuración de rutas
├── routes/                       # Routers FastAPI
│   ├── __init__.py
│   ├── dashboard.py             # Dashboard principal
│   ├── productos.py             # CRUD productos
│   ├── pedidos.py               # Gestión pedidos
│   ├── presupuestos.py          # Gestión presupuestos
│   ├── carritos.py              # Monitoreo carritos
│   └── usuarios.py              # Admin usuarios
├── Controllers/                 # Lógica de negocio (futuro)
│   └── __init__.py
├── schemas/                     # Validación datos (futuro)
│   └── __init__.py
├── middleware/                  # Middlewares
│   ├── __init__.py
│   └── admin_auth.py           # Autenticación admin
├── templates/                   # Vistas HTML
│   ├── dashboard.html          # ✅ Implementado
│   ├── productos.html          # ✅ Implementado
│   ├── pedidos.html            # 🔜 En desarrollo
│   ├── presupuestos.html       # 🔜 En desarrollo
│   ├── carritos.html           # 🔜 En desarrollo
│   └── usuarios.html           # 🔜 En desarrollo
└── static/                      # CSS, JS, imágenes
    ├── css/
    └── js/
```

## 🔧 Configuración en main.py

El panel se registra automáticamente en `main.py`:

```python
# Importar y configurar rutas del panel de administración
try:
    from Projects.Admin.routes_config import configure_admin_routes
    logger.info("Llamando a configure_admin_routes...")
    configure_admin_routes(app)
    logger.info("✅ Rutas del panel de administración configuradas correctamente")
except Exception as e:
    logger.error(f"❌ Error configurando rutas del panel de administración: {e}")
```

## 📊 Modelos Utilizados

### Tablas del Sistema Principal
- `Usuarios` - Usuarios administradores
- `Roles` - Roles del sistema
- `usuario_roles` - Relación muchos a muchos

### Tablas del Ecommerce
- `ecomerce_productos` - Productos
- `ecomerce_productos_variantes` - Variantes
- `ecomerce_categorias` - Categorías
- `ecomerce_pedidos` - Pedidos
- `ecomerce_pedido_items` - Items de pedidos
- `ecomerce_carritos` - Carritos
- `ecomerce_carrito_items` - Items de carritos
- `ecomerce_presupuesto` - Presupuestos
- `ecomerce_usuarios` - Usuarios clientes

## 🎨 Interfaz de Usuario

### Dashboard
- Tarjetas con estadísticas destacadas
- Gráficos y tablas de datos
- Diseño responsive y moderno
- Actualización dinámica con JavaScript

### Características de UX
- Navegación intuitiva entre secciones
- Filtros y búsqueda en todas las listas
- Feedback visual de acciones
- Confirmaciones para acciones críticas

## 🚧 Próximas Mejoras

### Corto Plazo
- [ ] Completar templates HTML de todas las secciones
- [ ] Agregar validación de formularios en frontend
- [ ] Implementar paginación en todas las listas
- [ ] Agregar confirmaciones antes de eliminar/desactivar

### Mediano Plazo
- [ ] Sistema de notificaciones en tiempo real
- [ ] Exportar reportes a PDF/Excel
- [ ] Gráficos interactivos con Chart.js
- [ ] Subida de imágenes de productos
- [ ] Editor WYSIWYG para descripciones

### Largo Plazo
- [ ] Panel de analytics avanzado
- [ ] Sistema de permisos granular
- [ ] Logs de auditoría
- [ ] API webhooks para integraciones
- [ ] Soporte multi-idioma

## 👨‍💻 Uso de la API

### Ejemplo: Obtener Estadísticas
```javascript
fetch('/admin/api/dashboard/stats', {
    headers: {
        'Authorization': 'Bearer <token>'
    }
})
.then(res => res.json())
.then(data => {
    console.log(data.productos.total); // Total de productos
    console.log(data.pedidos.pendientes); // Pedidos pendientes
    console.log(data.ventas.totales); // Ventas totales
});
```

### Ejemplo: Cambiar Estado de Pedido
```javascript
const formData = new FormData();
formData.append('nuevo_estado', 'enviado');

fetch('/admin/api/pedidos/123/estado', {
    method: 'PUT',
    headers: {
        'Authorization': 'Bearer <token>'
    },
    body: formData
})
.then(res => res.json())
.then(data => console.log(data.message));
```

## 📝 Logs y Debugging

Todos los eventos importantes se registran:
- Accesos al panel admin
- Creación/modificación de productos
- Cambios de estado en pedidos
- Activación/desactivación de usuarios
- Errores y excepciones

```python
logger.info(f"Acceso admin autorizado: {user.usuario}")
logger.warning(f"Usuario sin permisos intentó acceder: {user.usuario}")
logger.error(f"Error en validación de admin: {str(e)}")
```

## 🔒 Seguridad

### Validaciones Implementadas
✅ Autenticación JWT obligatoria
✅ Verificación de rol admin en cada request
✅ Validación de usuario activo
✅ Protección contra usuarios inactivos
✅ Evitar que admin se desactive a sí mismo
✅ Logging de eventos de seguridad

### Buenas Prácticas
- Nunca exponer información sensible en logs
- Validar todos los inputs del usuario
- Usar prepared statements (SQLAlchemy ORM)
- Sanitizar datos antes de loguear

## 📞 Soporte

Para dudas o problemas:
1. Revisar los logs del servidor
2. Verificar que el usuario tenga rol "admin"
3. Comprobar que la base de datos esté correcta
4. Revisar la consola del navegador (F12)

---

**Creado**: Noviembre 2025
**Versión**: 1.0.0
**Estado**: ✅ Funcional - En desarrollo activo
