# RUTAS DEL SISTEMA - USUARIOS

## Rutas Administrativas (Panel de Administracion)

### Gestion de Usuarios (CRUD)
- **URL de la pagina**: `http://127.0.0.1:8000/ecomerce/usuarios/pagina`
- **Archivo HTML**: `usuarios2.html`
- **Descripcion**: Panel administrativo para gestionar usuarios (crear, editar, eliminar)

### API Endpoints
- `GET /ecomerce/usuarios/` - Listar todos los usuarios
- `POST /ecomerce/usuarios/` - Crear nuevo usuario
- `GET /ecomerce/usuarios/id/{id}` - Obtener usuario por ID
- `PUT /ecomerce/usuarios/id/{id}` - Actualizar usuario
- `DELETE /ecomerce/usuarios/id/{id}` - Eliminar usuario

---

## Rutas de Usuario (Perfil Personal)

### Perfil de Usuario
- **URL de la pagina**: `http://127.0.0.1:8000/ecomerce/usuarios/perfil`
- **Archivo HTML**: `perfil.html`
- **Descripcion**: Perfil personal del usuario logueado con las siguientes secciones:
  - Editar informacion personal
  - Cambiar contraseña
  - Ver historial de pedidos
  - Ver carrito activo
  - Ver presupuestos solicitados

### API Endpoints del Perfil
- `GET /ecomerce/usuarios/profile` - Obtener datos completos del perfil
- `PUT /ecomerce/usuarios/profile` - Actualizar datos del perfil
- `POST /ecomerce/usuarios/change-password` - Cambiar contraseña
- `GET /ecomerce/usuarios/pedidos/user` - Obtener pedidos del usuario
- `GET /ecomerce/usuarios/carritos/active` - Obtener carrito activo
- `GET /ecomerce/usuarios/presupuestos/user` - Obtener presupuestos del usuario

---

## Archivos Importantes

### HTML Templates
- `usuarios2.html` - Panel administrativo de usuarios
- `perfil.html` - Perfil personal del usuario

### JavaScript
- `/static/js/usuarios.js` - Logica para el panel administrativo
- `/static/js/perfil.js` - Logica para el perfil personal

---

## Notas
- Todas las rutas requieren autenticacion via token JWT
- El perfil personal solo muestra datos del usuario logueado
- El panel administrativo requiere permisos de administrador
