# 🔐 Sistema de Validación Interna con Vencimiento

## 📋 Resumen

Este documento explica cómo funciona la validación interna de vencimiento para usuarios administradores que acceden al panel `/admin`.

## 🎯 Objetivo

Los usuarios admin tienen fechas de vencimiento que se sincronizan automáticamente con la API de proyectos, evitando consultas innecesarias en cada login.

## 🔄 Flujo de Validación

### 1️⃣ Login del Usuario Admin

```
Usuario ingresa credenciales en /admin/login
         ↓
Sistema valida email y contraseña
         ↓
¿Usuario tiene proyecto asignado?
    ├─ NO → Login exitoso sin validación de vencimiento
    │
    └─ SÍ → ¿Fecha de vencimiento es null o >= hoy?
            ├─ SÍ → Consultar API de proyectos
            │       ├─ Proyecto activo y fecha diferente
            │       │   → Actualizar fecha local
            │       └─ Proyecto inactivo
            │           → No actualizar (continuar con fecha local)
            │
            └─ NO → No consultar API (fecha ya vencida)
         ↓
Crear token JWT y permitir acceso
```

### 2️⃣ Peticiones Subsecuentes (con Token)

```
Usuario hace request a /admin/*
         ↓
Sistema valida token JWT
         ↓
Busca usuario en BD
         ↓
¿Usuario tiene fecha de vencimiento?
    ├─ NO → Acceso permitido (sin vencimiento)
    │
    └─ SÍ → ¿Fecha de vencimiento > ahora?
            ├─ SÍ → Acceso permitido
            └─ NO → Acceso denegado (vencido)
```

## 📊 Campos del Modelo AdminUsuarios

```python
class AdminUsuarios(Document):
    usuario: str                          # Username
    mail: EmailStr                        # Email
    clave_hash: str                       # Contraseña hasheada
    activo: bool                          # Estado activo/inactivo
    
    # NUEVOS CAMPOS para sistema de vencimiento
    proyecto_nombre: Optional[str]        # Nombre del proyecto asignado
    fecha_vencimiento: Optional[datetime] # Fecha de vencimiento (null = sin vencimiento)
```

## 🚀 Ejemplo de Flujo Completo

### Escenario: Usuario con fecha vencida necesita actualizar

**Estado inicial:**
- Usuario: `admin@example.com`
- Proyecto: `"Proyecto Demo"`
- Fecha local: `01/01/2026`
- Fecha actual: `11/01/2026`

**Proceso de login:**

1. Usuario ingresa credenciales
2. Sistema valida email y contraseña ✅
3. Detecta que `fecha_vencimiento (01/01/2026) >= fecha_actual (11/01/2026)` ❌ (está vencida)
4. **NO consulta API** porque ya venció
5. En requests subsecuentes, valida fecha local y **DENIEGA acceso**

### Escenario: Usuario con fecha próxima a vencer

**Estado inicial:**
- Usuario: `admin@example.com`
- Proyecto: `"Proyecto Demo"`
- Fecha local: `01/01/2026`
- Fecha actual: `28/12/2025` (antes del vencimiento)

**Proceso de login:**

1. Usuario ingresa credenciales
2. Sistema valida email y contraseña ✅
3. Detecta que `fecha_vencimiento (01/01/2026) >= fecha_actual (28/12/2025)` ✅
4. **SÍ consulta API** porque está próxima a vencer
5. API responde con nueva fecha: `01/04/2026`
6. Sistema actualiza fecha local: `01/01/2026` → `01/04/2026`
7. En requests subsecuentes, usa la nueva fecha local (`01/04/2026`)

## 💡 Ventajas del Sistema

### ✅ Eficiencia
- **No consulta API en cada login** cuando la fecha es válida y lejana
- Solo consulta cuando la fecha está próxima a vencer o ya venció
- Requests subsecuentes solo validan fecha local (sin API)

### ✅ Sincronización Automática
- Fechas se actualizan automáticamente durante el login
- No requiere intervención manual del usuario
- Mantiene sincronía con el sistema de proyectos

### ✅ Tolerancia a Fallos
- Si la API falla, continúa con la fecha local
- No bloquea el acceso por problemas de red
- Logs detallados de errores

## 🔧 Archivos Modificados/Creados

### Modelos
```
Projects/Admin/models/admin_usuarios_beanie.py
  ├─ Agregado: proyecto_nombre
  └─ Agregado: fecha_vencimiento
```

### Servicios
```
Projects/Admin/services/validacion_vencimiento.py (NUEVO)
  ├─ verificar_y_actualizar_vencimiento()
  └─ validar_acceso_admin()
```

### Autenticación
```
Projects/Admin/routes/auth.py
  └─ Login integrado con validación de vencimiento

security/jwt_auth.py
  └─ get_current_admin_user() valida fecha local
```

## 📝 Configuración Requerida

### 1. Variables de Entorno

Asegúrate de tener en tu `.env`:

```env
# URL de la API de proyectos (puede ser la misma app u otra instancia)
API_BASE_URL=http://127.0.0.1:8000
```

### 2. Inicializar Datos

```bash
# Crear proyectos y usuarios con vencimiento
python setup_proyectos_demo.py
```

Este script:
- Crea usuario admin con proyecto asignado
- Establece fecha de vencimiento
- Crea proyectos de ejemplo
- Crea vinculaciones en la API

## 🧪 Pruebas

### Test 1: Login con fecha válida (no consulta API)

```python
# Usuario con fecha_vencimiento = 01/12/2026 (muy lejana)
# Fecha actual = 11/01/2026
# Resultado: Login exitoso, NO consulta API
```

### Test 2: Login con fecha próxima (consulta API y actualiza)

```python
# Usuario con fecha_vencimiento = 15/01/2026 (próxima)
# Fecha actual = 11/01/2026
# API responde con fecha_vencimiento = 01/04/2026
# Resultado: Login exitoso, actualiza a 01/04/2026
```

### Test 3: Login con fecha vencida (no consulta API)

```python
# Usuario con fecha_vencimiento = 01/01/2026 (vencida)
# Fecha actual = 11/01/2026
# Resultado: Login bloqueado, NO consulta API
```

### Test 4: Requests subsecuentes

```python
# Usuario autenticado con token válido
# Hace request a /admin/dashboard
# Sistema valida solo fecha local
# Si está vencida: bloquea acceso
# Si es válida: permite acceso
```

## 🔍 Logs del Sistema

El sistema genera logs detallados:

```
[VALIDACIÓN INTERNA] Verificando vencimiento para admin - Proyecto: Proyecto Demo
[VALIDACIÓN INTERNA] Actualizando fecha para admin
   Fecha anterior: 2026-01-01 00:00:00
   Fecha nueva: 2026-04-01 00:00:00
✅ Fecha de vencimiento actualizada para admin: 2026-04-01 00:00:00
```

## ⚠️ Consideraciones Importantes

### Cuándo SE consulta la API
- ✅ Fecha de vencimiento es `null` (sin vencimiento establecido)
- ✅ Fecha de vencimiento es `>= fecha actual` (válida o próxima)
- ✅ Usuario tiene proyecto asignado
- ✅ Es un login (tenemos la contraseña)

### Cuándo NO SE consulta la API
- ❌ Fecha de vencimiento es `< fecha actual` (ya venció)
- ❌ Usuario sin proyecto asignado
- ❌ Requests subsecuentes (solo valida fecha local)
- ❌ API no disponible (continúa con fecha local)

### Timeout de API
- Configurado a **5 segundos**
- Si falla, no bloquea el login
- Continúa con fecha local

## 🎯 Casos de Uso

### Caso 1: Usuario Nuevo
```
1. Admin crea usuario con proyecto y fecha de vencimiento
2. Usuario hace login por primera vez
3. Sistema consulta API y sincroniza fecha
4. Usuario trabaja normalmente
```

### Caso 2: Extensión de Acceso
```
1. Admin extiende fecha en el sistema de proyectos
2. Usuario hace login (antes de que venza la fecha local)
3. Sistema detecta fecha próxima y consulta API
4. Actualiza fecha local automáticamente
5. Usuario continúa trabajando sin interrupciones
```

### Caso 3: Revocación de Acceso
```
1. Admin desactiva proyecto o vinculación
2. Usuario hace login
3. Sistema consulta API y detecta rechazo
4. No actualiza fecha local
5. Cuando vence la fecha local, acceso es bloqueado
```

## 📞 Troubleshooting

### Error: "Su acceso ha vencido"
**Causa:** La fecha de vencimiento local es menor a la fecha actual.
**Solución:** 
1. Contactar al administrador del sistema
2. Verificar estado en la API de proyectos
3. Administrador puede extender la fecha

### Error en validación de API
**Causa:** API no disponible o timeout.
**Solución:** Sistema continúa con fecha local, no es crítico.

### Fecha no se actualiza
**Causa:** API devuelve la misma fecha o error.
**Solución:** Verificar logs y estado del proyecto en la API.

---

**Estado:** ✅ Sistema completamente funcional

**Última actualización:** Enero 2026
