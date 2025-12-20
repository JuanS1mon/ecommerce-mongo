import requests
import uuid
BASE='http://127.0.0.1:8000'
unique=uuid.uuid4().hex[:8]
email=f'pw_user_{unique}@example.com'
payload={'nombre':'PW','apellido':'Tester','email':email,'contraseña':'TestPass123!'}
r=requests.post(f'{BASE}/ecomerce/auth/register', json=payload, timeout=5)
print('status',r.status_code)
print('text',r.text)
