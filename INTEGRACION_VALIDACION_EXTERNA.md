# 🔐 GUÍA DE INTEGRACIÓN - VALIDACIÓN DE USUARIOS DESDE APLICACIONES EXTERNAS

## 📋 Resumen

Esta guía explica cómo integrar tu aplicación externa con el sistema de autenticación centralizado para validar usuarios y verificar su acceso a proyectos específicos.

---

## 🎯 Endpoint de Validación

### URL del Endpoint
```
POST {API_BASE_URL}/api/v1/validate
```

**Configuración de URL:**
- **Desarrollo local:** `http://127.0.0.1:8000/api/v1/validate`
- **Producción:** Configura `API_BASE_URL` en tu archivo `.env`
- **Azure/Cloud:** `https://tu-app.azurewebsites.net/api/v1/validate`

**Importante:** 
- La URL debe configurarse según tu entorno
- Usa variables de entorno para manejar diferentes URLs
- Nunca hardcodees URLs en tu código de producción

### Características
- ✅ **No requiere autenticación** (endpoint público)
- ✅ **CORS habilitado** (acepta requests desde cualquier origen)
- ✅ **Validación completa** (credenciales + proyecto + vencimiento)
- ✅ **Tracking automático** de intentos de acceso

---

## 📤 Request

### Headers
```http
Content-Type: application/json
```

### Body (JSON)
```json
{
  "email": "usuario@ejemplo.com",
  "password": "password_del_usuario",
  "proyecto_nombre": "Nombre del Proyecto"
}
```

### Campos Requeridos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `email` | string | Email del usuario registrado en el sistema |
| `password` | string | Contraseña del usuario |
| `proyecto_nombre` | string | Nombre exacto del proyecto (case-sensitive) |

---

## 📥 Response

### Respuesta Exitosa (200 OK)
```json
{
  "valid": true,
  "mensaje": "Acceso válido",
  "datos_usuario": {
    "email": "usuario@ejemplo.com",
    "username": "juanperez"
  },
  "fecha_vencimiento": "2027-01-11T23:59:59Z"
}
```

### Respuesta de Rechazo (200 OK)
```json
{
  "valid": false,
  "mensaje": "Usuario no asignado a este proyecto"
}
```

### Campos de Respuesta

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `valid` | boolean | `true` si el acceso es válido, `false` si no |
| `mensaje` | string | Descripción del resultado |
| `datos_usuario` | object | Solo presente si `valid: true` |
| `datos_usuario.email` | string | Email del usuario |
| `datos_usuario.username` | string | Nombre de usuario |
| `fecha_vencimiento` | string | Solo presente si `valid: true`. Fecha ISO 8601 |

---

## ❌ Casos de Rechazo

El sistema retorna `valid: false` en los siguientes casos:

| Caso | Mensaje |
|------|---------|
| Credenciales incorrectas | `"Credenciales inválidas"` |
| Usuario inactivo | `"Usuario no está activo"` |
| Proyecto no existe | `"Proyecto no encontrado"` |
| Proyecto inactivo | `"El proyecto no está activo"` |
| Usuario no asignado | `"Usuario no asignado a este proyecto"` |
| Acceso vencido | `"El acceso al proyecto ha vencido"` |
| Vinculación inactiva | `"La vinculación está inactiva"` |

---

## 💻 Ejemplos de Implementación

### Python (Requests)
```python
import requests
from datetime import datetime

def validar_acceso(email, password, proyecto):
    """
    Valida el acceso de un usuario a un proyecto específico.
    
    Returns:
        dict: {"acceso_permitido": bool, "datos_usuario": dict, "vencimiento": datetime}
    """
    url = "http://127.0.0.1:8000/api/v1/validate"
    
    payload = {
        "email": email,
        "password": password,
        "proyecto_nombre": proyecto
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if data["valid"]:
            return {
                "acceso_permitido": True,
                "datos_usuario": data["datos_usuario"],
                "vencimiento": datetime.fromisoformat(data["fecha_vencimiento"].replace('Z', '+00:00')),
                "mensaje": data["mensaje"]
            }
        else:
            return {
                "acceso_permitido": False,
                "datos_usuario": None,
                "vencimiento": None,
                "mensaje": data["mensaje"]
            }
    
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")
        return {
            "acceso_permitido": False,
            "datos_usuario": None,
            "vencimiento": None,
            "mensaje": "Error de conexión con servidor de autenticación"
        }

# Uso
resultado = validar_acceso(
    email="usuario@ejemplo.com",
    password="mi_password",
    proyecto="CRM Ventas 2026"
)

if resultado["acceso_permitido"]:
    print(f"✅ Acceso permitido para {resultado['datos_usuario']['username']}")
    print(f"📅 Vence: {resultado['vencimiento']}")
else:
    print(f"❌ Acceso denegado: {resultado['mensaje']}")
```

---

### JavaScript/Node.js (Fetch)
```javascript
async function validarAcceso(email, password, proyectoNombre) {
    const url = 'http://127.0.0.1:8000/api/v1/validate';
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                password: password,
                proyecto_nombre: proyectoNombre
            })
        });
        
        const data = await response.json();
        
        if (data.valid) {
            return {
                accesoPermitido: true,
                usuario: data.datos_usuario,
                vencimiento: new Date(data.fecha_vencimiento),
                mensaje: data.mensaje
            };
        } else {
            return {
                accesoPermitido: false,
                mensaje: data.mensaje
            };
        }
    } catch (error) {
        console.error('Error de conexión:', error);
        return {
            accesoPermitido: false,
            mensaje: 'Error de conexión con servidor de autenticación'
        };
    }
}

// Uso
const resultado = await validarAcceso(
    'usuario@ejemplo.com',
    'mi_password',
    'CRM Ventas 2026'
);

if (resultado.accesoPermitido) {
    console.log(`✅ Acceso permitido para ${resultado.usuario.username}`);
    console.log(`📅 Vence: ${resultado.vencimiento}`);
} else {
    console.log(`❌ Acceso denegado: ${resultado.mensaje}`);
}
```

---

### C# (.NET)
```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public class ValidacionService
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl = "http://127.0.0.1:8000";

    public ValidacionService()
    {
        _httpClient = new HttpClient();
    }

    public async Task<ResultadoValidacion> ValidarAcceso(string email, string password, string proyectoNombre)
    {
        var request = new
        {
            email = email,
            password = password,
            proyecto_nombre = proyectoNombre
        };

        var json = JsonSerializer.Serialize(request);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        try
        {
            var response = await _httpClient.PostAsync($"{_baseUrl}/api/v1/validate", content);
            response.EnsureSuccessStatusCode();

            var responseBody = await response.Content.ReadAsStringAsync();
            var resultado = JsonSerializer.Deserialize<ValidacionResponse>(responseBody);

            return new ResultadoValidacion
            {
                AccesoPermitido = resultado.valid,
                Mensaje = resultado.mensaje,
                Usuario = resultado.datos_usuario,
                FechaVencimiento = resultado.fecha_vencimiento != null 
                    ? DateTime.Parse(resultado.fecha_vencimiento) 
                    : null
            };
        }
        catch (Exception ex)
        {
            return new ResultadoValidacion
            {
                AccesoPermitido = false,
                Mensaje = $"Error de conexión: {ex.Message}"
            };
        }
    }
}

public class ValidacionResponse
{
    public bool valid { get; set; }
    public string mensaje { get; set; }
    public DatosUsuario datos_usuario { get; set; }
    public string fecha_vencimiento { get; set; }
}

public class DatosUsuario
{
    public string email { get; set; }
    public string username { get; set; }
}

public class ResultadoValidacion
{
    public bool AccesoPermitido { get; set; }
    public string Mensaje { get; set; }
    public DatosUsuario Usuario { get; set; }
    public DateTime? FechaVencimiento { get; set; }
}

// Uso
var servicio = new ValidacionService();
var resultado = await servicio.ValidarAcceso(
    "usuario@ejemplo.com",
    "mi_password",
    "CRM Ventas 2026"
);

if (resultado.AccesoPermitido)
{
    Console.WriteLine($"✅ Acceso permitido para {resultado.Usuario.username}");
    Console.WriteLine($"📅 Vence: {resultado.FechaVencimiento}");
}
else
{
    Console.WriteLine($"❌ Acceso denegado: {resultado.Mensaje}");
}
```

---

### PHP
```php
<?php
function validarAcceso($email, $password, $proyectoNombre) {
    $url = 'http://127.0.0.1:8000/api/v1/validate';
    
    $data = array(
        'email' => $email,
        'password' => $password,
        'proyecto_nombre' => $proyectoNombre
    );
    
    $options = array(
        'http' => array(
            'header'  => "Content-Type: application/json\r\n",
            'method'  => 'POST',
            'content' => json_encode($data),
            'timeout' => 5
        )
    );
    
    $context = stream_context_create($options);
    $response = @file_get_contents($url, false, $context);
    
    if ($response === FALSE) {
        return array(
            'acceso_permitido' => false,
            'mensaje' => 'Error de conexión con servidor de autenticación'
        );
    }
    
    $resultado = json_decode($response, true);
    
    if ($resultado['valid']) {
        return array(
            'acceso_permitido' => true,
            'usuario' => $resultado['datos_usuario'],
            'vencimiento' => $resultado['fecha_vencimiento'],
            'mensaje' => $resultado['mensaje']
        );
    } else {
        return array(
            'acceso_permitido' => false,
            'mensaje' => $resultado['mensaje']
        );
    }
}

// Uso
$resultado = validarAcceso(
    'usuario@ejemplo.com',
    'mi_password',
    'CRM Ventas 2026'
);

if ($resultado['acceso_permitido']) {
    echo "✅ Acceso permitido para " . $resultado['usuario']['username'] . "\n";
    echo "📅 Vence: " . $resultado['vencimiento'] . "\n";
} else {
    echo "❌ Acceso denegado: " . $resultado['mensaje'] . "\n";
}
?>
```

---

## 🔄 Flujo de Integración Recomendado

### 1. Login en tu Aplicación

```
Usuario ingresa credenciales en tu app
         ↓
Tu app llama a POST /api/v1/validate
         ↓
    ¿valid: true?
    ├─ SÍ → Crear sesión local
    │        Guardar fecha_vencimiento
    │        Permitir acceso
    │
    └─ NO → Mostrar error
             Denegar acceso
```

### 2. Verificación Periódica (Opcional)

Para aplicaciones de larga duración, considera verificar periódicamente:

```python
# Verificar al inicio de cada sesión o cada X horas
if tiempo_desde_ultima_verificacion > 24_horas:
    resultado = validar_acceso(email, password, proyecto)
    if not resultado["acceso_permitido"]:
        cerrar_sesion()
        redirigir_a_login()
```

### 3. Manejo de Fecha de Vencimiento

```javascript
// Almacenar en localStorage/sessionStorage
if (resultado.accesoPermitido) {
    localStorage.setItem('usuario_email', resultado.usuario.email);
    localStorage.setItem('vencimiento', resultado.vencimiento);
    
    // Verificar vencimiento en cada carga
    const vencimiento = new Date(localStorage.getItem('vencimiento'));
    if (new Date() > vencimiento) {
        alert('Tu acceso ha vencido. Contacta al administrador.');
        cerrarSesion();
    }
}
```

---

## 🛡️ Seguridad y Mejores Prácticas

### ✅ Recomendaciones

1. **Usar HTTPS en Producción**
   ```
   https://tu-dominio.com/api/v1/validate
   ```

2. **No Almacenar Contraseñas**
   - Solo envía la contraseña durante la validación
   - No la guardes en localStorage ni cookies

3. **Timeout Razonable**
   - Configura timeout de 5-10 segundos máximo
   - Maneja errores de conexión gracefully

4. **Caché con Precaución**
   - Puedes cachear la validación por 1-4 horas
   - Siempre verifica la fecha de vencimiento localmente

5. **Logging**
   - Registra intentos de acceso fallidos
   - No loguees contraseñas

6. **Rate Limiting (Cliente)**
   - Limita reintentos tras fallos
   - Implementa backoff exponencial

### ⚠️ Evitar

❌ Enviar contraseñas en URL (GET parameters)
❌ Almacenar contraseñas en texto plano
❌ Hardcodear credenciales en código
❌ Ignorar el campo `valid` de la respuesta
❌ Confiar solo en validación client-side

---

## 📊 Tracking Automático

El sistema registra automáticamente:

- ✅ `last_validation_attempt` - Todos los intentos (exitosos y fallidos)
- ✅ `last_validated_at` - Solo accesos exitosos

Puedes ver estos datos en el dashboard admin:
```
Dashboard → Usuarios → Columna "Último Acceso"
```

---

## 🧪 Testing

### Caso de Prueba 1: Login Exitoso
```bash
curl -X POST http://127.0.0.1:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "password123",
    "proyecto_nombre": "CRM Ventas 2026"
  }'
```

**Respuesta esperada:**
```json
{
  "valid": true,
  "mensaje": "Acceso válido",
  "datos_usuario": {...},
  "fecha_vencimiento": "2027-01-11T23:59:59Z"
}
```

### Caso de Prueba 2: Contraseña Incorrecta
```bash
curl -X POST http://127.0.0.1:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "incorrecta",
    "proyecto_nombre": "CRM Ventas 2026"
  }'
```

**Respuesta esperada:**
```json
{
  "valid": false,
  "mensaje": "Credenciales inválidas"
}
```

### Caso de Prueba 3: Proyecto No Existe
```bash
curl -X POST http://127.0.0.1:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "password123",
    "proyecto_nombre": "Proyecto Inexistente"
  }'
```

**Respuesta esperada:**
```json
{
  "valid": false,
  "mensaje": "Proyecto no encontrado"
}
```

---

## 🚀 Configuración de Producción

### Variables de Entorno

Crea un archivo `.env` en tu aplicación:

```env
AUTH_API_URL=https://api.tudominio.com/api/v1/validate
AUTH_PROYECTO_NOMBRE=Nombre de Tu Proyecto
AUTH_TIMEOUT=10
```

### Ejemplo de Uso
```python
import os
from dotenv import load_dotenv

load_dotenv()

AUTH_URL = os.getenv('AUTH_API_URL')
PROYECTO = os.getenv('AUTH_PROYECTO_NOMBRE')

resultado = validar_acceso(email, password, PROYECTO)
```

---

## 📞 Soporte

### ¿Problemas con la Integración?

1. **Verifica que el servidor esté corriendo:**
   ```bash
   curl http://127.0.0.1:8000/docs
   ```

2. **Revisa los logs del servidor FastAPI**

3. **Confirma que el proyecto existe:**
   - Dashboard → Proyectos → Busca el nombre exacto

4. **Verifica que el usuario esté asignado:**
   - Dashboard → Usuarios → Ver Proyectos del usuario

5. **Comprueba la fecha de vencimiento:**
   - Dashboard → Usuarios → Verifica que no esté vencido

---

## 📝 Checklist de Integración

Antes de ir a producción, verifica:

- [ ] Endpoint de validación funciona desde tu app
- [ ] Manejo de errores implementado
- [ ] Timeout configurado (5-10 segundos)
- [ ] HTTPS habilitado en producción
- [ ] Variables de entorno configuradas
- [ ] Logging de errores activado
- [ ] Fecha de vencimiento verificada localmente
- [ ] Mensajes de error claros para el usuario
- [ ] Testing con credenciales válidas e inválidas
- [ ] Rate limiting implementado (opcional)

---

## 🎯 Resumen Rápido

**Para integrar tu app:**

1. Haz POST a `/api/v1/validate` con email, password y proyecto_nombre
2. Si `valid: true` → Permitir acceso y guardar fecha_vencimiento
3. Si `valid: false` → Denegar acceso y mostrar mensaje
4. Verificar fecha de vencimiento localmente
5. (Opcional) Re-validar cada 24 horas

**¡Eso es todo!** 🎉

---

## 📚 Recursos Adicionales

- **Documentación API:** `{API_BASE_URL}/docs`
- **Dashboard Admin:** `{API_BASE_URL}/admin/dashboard`
- **Endpoint de validación:** `POST {API_BASE_URL}/api/v1/validate`

---

## ⚙️ CONFIGURACIÓN DEL SISTEMA

### 1. Variables de Entorno

Agrega esta variable a tu archivo `.env`:

```env
# API Base URL - Para integraciones externas
# En desarrollo: http://127.0.0.1:8000
# En producción: https://tu-dominio.com (sin trailing slash)
API_BASE_URL=http://127.0.0.1:8000
```

### 2. Inicializar Base de Datos

Si es la primera vez que usas el sistema de proyectos, ejecuta:

```bash
# Crear proyectos y vinculaciones de ejemplo
python setup_proyectos_demo.py
```

Este script creará:
- ✅ Usuario admin por defecto (admin@example.com / admin123)
- ✅ 4 proyectos de ejemplo
- ✅ Vinculaciones con diferentes fechas de vencimiento

### 3. Probar la Integración

Usa el script de prueba incluido:

```bash
# Ejecutar ejemplos completos
python test_validacion_externa.py

# Modo interactivo
python test_validacion_externa.py simple
```

### 4. Estructura de Archivos Creados

```
📁 Proyecto
├── 📄 Projects/Admin/models/proyectos_beanie.py        # Modelos Proyecto y UsuarioProyecto
├── 📄 Projects/Admin/schemas/validacion_externa.py     # Schemas de request/response
├── 📄 Projects/Admin/routes/validacion_externa.py      # Router con endpoint /api/v1/validate
├── 📄 setup_proyectos_demo.py                           # Script de inicialización
├── 📄 test_validacion_externa.py                        # Script de prueba
└── 📄 INTEGRACION_VALIDACION_EXTERNA.md                 # Esta guía
```

### 5. Gestión de Proyectos (Próximamente)

Para gestionar proyectos vía dashboard admin, los datos se almacenan en MongoDB:

**Colecciones:**
- `proyectos` - Lista de proyectos disponibles
- `usuario_proyectos` - Vinculaciones usuario-proyecto con fechas

**Campos importantes:**
- `activo` - Estado del proyecto/vinculación
- `fecha_vencimiento` - Null = sin vencimiento
- `last_validated_at` - Última validación exitosa
- `last_validation_attempt` - Último intento (exitoso o fallido)

---

## 🔧 Troubleshooting

### Error: "Proyecto no encontrado"
- ✅ Verifica que el nombre sea exacto (case-sensitive)
- ✅ Confirma que el proyecto existe en la colección `proyectos`
- ✅ Ejecuta `setup_proyectos_demo.py` para crear datos de ejemplo

### Error: "Usuario no asignado a este proyecto"
- ✅ Verifica que exista una vinculación en `usuario_proyectos`
- ✅ Confirma que la vinculación tenga `activo: true`
- ✅ Verifica los IDs: `usuario_id` y `proyecto_id`

### Error: "El acceso al proyecto ha vencido"
- ✅ Revisa el campo `fecha_vencimiento` en la vinculación
- ✅ Actualiza la fecha o establece en `null` para acceso permanente

### Error de conexión
- ✅ Verifica que el servidor esté corriendo
- ✅ Confirma la URL en `API_BASE_URL`
- ✅ Revisa que MongoDB esté conectado

---

## 🚀 Deployment en Producción

### 1. Configurar Variables de Entorno

```bash
# En Azure App Service / Cloud
API_BASE_URL=https://tu-app.azurewebsites.net

# En servidor propio
API_BASE_URL=https://api.tudominio.com
```

### 2. Consideraciones de Seguridad

- ✅ Usa HTTPS en producción (obligatorio)
- ✅ Configura rate limiting en el servidor
- ✅ Implementa logging de intentos fallidos
- ✅ Monitorea accesos sospechosos
- ✅ Revisa periódicamente las vinculaciones activas

### 3. Performance

- ✅ Los modelos tienen índices en MongoDB para búsquedas rápidas
- ✅ El endpoint es público pero ligero
- ✅ Considera caché de validaciones exitosas (1-4 horas)
- ✅ Implementa timeout de 5-10 segundos en el cliente

---

## 📞 Soporte Técnico

**Logs del servidor:**
```bash
# Ver logs en tiempo real
tail -f app.log

# Buscar validaciones
grep "VALIDACIÓN" app.log
```

**Verificar datos en MongoDB:**
```javascript
// Proyectos
db.proyectos.find()

// Vinculaciones
db.usuario_proyectos.find()

// Usuario admin
db.admin_usuarios.findOne({mail: "admin@example.com"})
```

---

## ✅ Checklist Final de Implementación

Antes de ir a producción:

- [ ] ✅ Variable `API_BASE_URL` configurada en `.env`
- [ ] ✅ Modelos registrados en `database.py`
- [ ] ✅ Router incluido en `main.py`
- [ ] ✅ Proyectos creados en MongoDB
- [ ] ✅ Usuarios asignados a proyectos
- [ ] ✅ Fechas de vencimiento configuradas
- [ ] ✅ Endpoint probado localmente
- [ ] ✅ Script de prueba ejecutado exitosamente
- [ ] ✅ Documentación API revisada en `/docs`
- [ ] ✅ HTTPS configurado en producción
- [ ] ✅ Logging funcionando correctamente
- [ ] ✅ Rate limiting implementado (opcional)
- [ ] ✅ Monitoreo de accesos configurado

---

**¡Sistema listo para integraciones externas!** 🎉
