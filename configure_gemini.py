#!/usr/bin/env python3
"""
Script para configurar API Key de Gemini para Marketing
"""
import asyncio
import httpx

async def configure_gemini_api():
    print("🔧 Configuración de API Key de Gemini")
    print("=" * 50)

    # Solicitar nueva API key
    api_key = input("Ingresa tu nueva API Key de Gemini (o presiona Enter para usar la actual): ").strip()

    if not api_key:
        print("❌ No se proporcionó API key. Saliendo...")
        return

    async with httpx.AsyncClient() as client:
        try:
            # Login
            login_data = {'username': 'juanadmin', 'password': '123456'}
            login_response = await client.post('http://127.0.0.1:8001/admin/api/login', data=login_data)

            if login_response.status_code != 200:
                print("❌ Error de login. Verifica credenciales.")
                return

            token = login_response.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}'}

            # Configurar API key
            config_data = {
                'google_ai_api_key': api_key,
                'modelo_ia': 'gemini-2.0-flash',
                'max_tokens_por_request': '1000',
                'temperatura': '0.7',
                'activo': 'true'
            }

            update_response = await client.post('http://127.0.0.1:8001/admin/marketing/api/config', data=config_data, headers=headers)

            if update_response.status_code == 200:
                print("✅ API Key configurada exitosamente!")
                print("🔄 Reinicia el servidor para aplicar los cambios.")
            else:
                print(f"❌ Error al configurar API key: {update_response.text}")

        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(configure_gemini_api())