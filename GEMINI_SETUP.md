# Configuración de Gemini AI para Chat de Marketing

## Estado Actual
✅ **Funcionalidad implementada y probada**
- Chat de IA integrado en página de creación de campañas
- Manejo de errores implementado
- Configuración vía API REST

⚠️ **API Key actual excedió cuota gratuita**
- Se muestra mensaje claro al usuario
- Requiere API key con cuota disponible

## Cómo Configurar una Nueva API Key

### 1. Obtener API Key de Google AI Studio
1. Ve a [Google AI Studio](https://aistudio.google.com/)
2. Inicia sesión con tu cuenta Google
3. Crea un nuevo proyecto o selecciona uno existente
4. Ve a "API Keys" en el menú lateral
5. Crea una nueva API key
6. Copia la API key generada

### 2. Configurar en la Aplicación
Ejecuta el script de configuración:

```bash
# Asegúrate de que el servidor esté ejecutándose
python configure_gemini.py
```

Ingresa tu nueva API key cuando se solicite.

### 3. Verificar Configuración
```bash
python check_config_api.py
```

### 4. Probar Funcionalidad
```bash
python test_chat_gemini.py
```

## Modelos Disponibles
- `gemini-2.0-flash` (recomendado - rápido y eficiente)
- `gemini-2.0-flash-exp` (experimental)
- `gemini-pro-latest` (última versión estable)

## Solución de Problemas

### Error de Cuota
- Verifica tu plan de facturación en Google AI Studio
- Considera actualizar a un plan pago

### Error de API Key
- Verifica que la API key sea correcta
- Asegúrate de que esté habilitada la API de Gemini

### Error de Modelo
- Usa uno de los modelos listados arriba
- Verifica que el modelo esté disponible en tu región

## Configuración Manual
Si prefieres configurar manualmente:

1. Ve a `/admin/marketing/config` en tu aplicación
2. Ingresa tu API key en el campo "Google AI API Key"
3. Selecciona el modelo deseado
4. Guarda la configuración

## Notas Importantes
- La API key se almacena de forma segura en la base de datos
- Se recomienda rotar las API keys periódicamente
- Monitorea el uso en Google AI Studio para evitar sorpresas en la facturación