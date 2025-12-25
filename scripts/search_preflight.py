import zipfile
z=zipfile.ZipFile('site_logs.zip')
keywords=['Preflight: import falló','Preflight: import fallo','Preflight: import failed','IMPORT_OK','import_check','Preflight: import']
found=[]
for name in z.namelist():
    try:
        data=z.read(name).decode('utf-8',errors='ignore')
    except Exception:
        continue
    for kw in keywords:
        if kw in data:
            found.append((name,kw))
            break
print(found)
