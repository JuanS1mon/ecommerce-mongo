# 🧪 Guía de Pruebas - Validación de Usuarios Ecomerce

## 📋 Configuración Inicial

### 1. Variables de Entorno Configuradas

```env
# En tu archivo .env
API_BASE_URL=http://127.0.0.1:8000
ADMIN_PROYECTO_NOMBRE=Ecomerce
```

✅ Ya están configuradas en tu `.env`

### 2. Usuarios de Prueba

| Email | Username | Proyecto | Vencimiento | Estado | Descripción |
|-------|----------|----------|-------------|--------|-------------|
| admin@sysneg.com | admin | Ecomerce | 3/7/2026 | ✅ Activo | Usuario NO vencido (172 días) |
| fjuansimon@gmail.com | juan | Ecomerce | 1/1/2026 | ❌ Inactivo | Usuario VENCIDO (venció hace 10 días) |

---

## 🚀 Pasos para Probar

### Paso 1: Configurar Usuarios en la Base de Datos

```bash
# Configura los usuarios con sus proyectos y fechas
python configurar_usuarios_ecomerce.py
```

**Qué hace este script:**
- ✅ Crea/actualiza los usuarios admin@sysneg.com y fjuansimon@gmail.com
- ✅ Asigna el proyecto "Ecomerce" a ambos
- ✅ Establece las fechas de vencimiento (3/7/2026 y 1/1/2026)
- ✅ Crea el proyecto en la API si no existe
- ✅ Crea las vinculaciones usuario-proyecto

**⚠️ IMPORTANTE:** Antes de ejecutar, ajusta las contraseñas en el script (líneas 36 y 45).

---

### Paso 2: Ejecutar Tests Automatizados

```bash
# Prueba ambos usuarios automáticamente
python test_usuarios_ecomerce.py
```

**Qué hace este script:**
- 🧪 Prueba el usuario NO vencido (admin@sysneg.com)
- 🧪 Prueba el usuario VENCIDO (fjuansimon@gmail.com)
- 📊 Muestra validación local y con API
- 📋 Genera reporte completo de resultados

**⚠️ IMPORTANTE:** Ajusta las contraseñas en el script (líneas 72 y 86).

---

### Paso 3: Iniciar el Servidor

```powershell
# Activa el entorno virtual
.\.venv_test\Scripts\Activate.ps1

# Inicia el servidor
uvicorn main:app --reload
```

---

### Paso 4: Pruebas Manuales en el Navegador

#### 🟢 Prueba 1: Usuario NO Vencido

1. Abre: `http://127.0.0.1:8000/admin/login`
2. Ingresa credenciales:
   - **Email:** `admin@sysneg.com`
   - **Password:** `admin123` (o la que configuraste)
3. Observa los logs del servidor

**Resultado Esperado:**
```
[VALIDACIÓN INTERNA] Verificando vencimiento para admin - Proyecto: Ecomerce
[VALIDACIÓN INTERNA] Actualizando fecha para admin (o sin cambios)
✅ Login admin exitoso: admin desde [IP]
```

**En el navegador:**
- ✅ Login exitoso
- ✅ Redirección a /admin/dashboard
- ✅ Acceso completo al panel

---

#### 🔴 Prueba 2: Usuario VENCIDO

1. Cierra sesión del usuario anterior
2. Accede nuevamente a: `http://127.0.0.1:8000/admin/login`
3. Ingresa credenciales:
   - **Email:** `fjuansimon@gmail.com`
   - **Password:** `juan123` (o la que configuraste)
4. Observa los logs del servidor

**Resultado Esperado:**
```
[VALIDACIÓN] Acceso vencido para juan. Vencimiento: 2026-01-01...
❌ Admin con acceso vencido intentó acceder: juan
```

**En el navegador:**
- ❌ Error: "Su acceso ha vencido. Contacte al administrador del sistema."
- ❌ No se permite el acceso

---

## 🔍 Comportamiento del Sistema

### Usuario NO Vencido (admin@sysneg.com)

```
1. Usuario hace login con credenciales
         ↓
2. Sistema valida email y contraseña ✅
         ↓
3. Detecta: fecha_vencimiento (3/7/2026) >= fecha_actual (11/1/2026) ✅
         ↓
4. SÍ CONSULTA API (fecha válida)
         ↓
5. API responde con fecha de vencimiento del proyecto
         ↓
6. Si cambió, ACTUALIZA fecha local
         ↓
7. Crea token JWT y permite acceso ✅
         ↓
8. En requests subsecuentes: Solo valida fecha local (no consulta API)
```

### Usuario VENCIDO (fjuansimon@gmail.com)

```
1. Usuario hace login con credenciales
         ↓
2. Sistema valida email y contraseña ✅
         ↓
3. Detecta: fecha_vencimiento (1/1/2026) < fecha_actual (11/1/2026) ❌
         ↓
4. NO CONSULTA API (ya venció)
         ↓
5. En la validación JWT: Verifica fecha local
         ↓
6. Fecha vencida: DENIEGA acceso ❌
```

---

## 📊 Verificar Logs

### Logs Esperados para Usuario NO Vencido

```
[VALIDACIÓN INTERNA] Verificando vencimiento para admin - Proyecto: Ecomerce
[INFO] Consultando API: http://127.0.0.1:8000/api/v1/validate
[VALIDACIÓN INTERNA] Actualizando fecha para admin
   Fecha anterior: 2026-07-03 23:59:59
   Fecha nueva: 2026-07-03 23:59:59 (o diferente si cambió en la API)
✅ Fecha de vencimiento actualizada para admin: 2026-07-03 23:59:59
✅ Login admin exitoso: admin desde 127.0.0.1
[DEBUG] Admin autenticado: admin
```

### Logs Esperados para Usuario VENCIDO

```
[VALIDACIÓN] Acceso vencido para juan. Vencimiento: 2026-01-01 23:59:59
❌ Admin con acceso vencido intentó acceder: juan
[WARNING] Admin con acceso vencido intentó acceder: juan
```

---

## 🔧 Troubleshooting

### Problema: "Usuario no encontrado"

**Solución:** Ejecuta `python configurar_usuarios_ecomerce.py`

### Problema: "Credenciales inválidas"

**Solución:** Verifica/ajusta las contraseñas en:
- `configurar_usuarios_ecomerce.py` (líneas 36 y 45)
- `test_usuarios_ecomerce.py` (líneas 72 y 86)

### Problema: "Proyecto no encontrado" en la API

**Solución:** 
1. Verifica que el proyecto "Ecomerce" existe en la colección `proyectos`
2. Verifica que hay vinculaciones en `usuario_proyectos`
3. Ejecuta `configurar_usuarios_ecomerce.py` para crearlos

### Problema: Error al consultar API

**Solución:**
1. Verifica que el servidor está corriendo en `http://127.0.0.1:8000`
2. Verifica que el endpoint `/api/v1/validate` responde
3. Prueba manualmente con curl:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@sysneg.com",
    "password": "admin123",
    "proyecto_nombre": "Ecomerce"
  }'
```

---

## 📝 Checklist de Pruebas

Antes de reportar problemas, verifica:

- [ ] Variables de entorno configuradas (`API_BASE_URL`, `ADMIN_PROYECTO_NOMBRE`)
- [ ] Usuarios configurados con `configurar_usuarios_ecomerce.py`
- [ ] Contraseñas correctas en los scripts
- [ ] Servidor corriendo en `http://127.0.0.1:8000`
- [ ] Proyecto "Ecomerce" existe en la BD
- [ ] Vinculaciones usuario-proyecto creadas
- [ ] Endpoint `/api/v1/validate` funciona
- [ ] MongoDB conectado correctamente

---

## 📞 Resultados Esperados

### ✅ Usuario NO Vencido (admin@sysneg.com)

| Aspecto | Resultado |
|---------|-----------|
| Login | ✅ Exitoso |
| Consulta API | ✅ Sí (si fecha >= hoy) |
| Actualiza fecha | ✅ Si cambió en API |
| Acceso dashboard | ✅ Permitido |
| Requests subsecuentes | ✅ Solo valida local |

### ❌ Usuario VENCIDO (fjuansimon@gmail.com)

| Aspecto | Resultado |
|---------|-----------|
| Login | ❌ Bloqueado |
| Consulta API | ❌ No (ya venció) |
| Actualiza fecha | ❌ No consulta |
| Acceso dashboard | ❌ Denegado |
| Mensaje error | "Su acceso ha vencido..." |

---

**¡Listo para probar!** 🚀

Ejecuta los pasos en orden y verifica que el comportamiento sea el esperado.
