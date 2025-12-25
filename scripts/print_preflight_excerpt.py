import zipfile,re
z=zipfile.ZipFile('site_logs.zip')
name='LogFiles/2025_12_25_lw1sdlwk0001LW_default_docker.log'
if name in z.namelist():
    data=z.read(name).decode('utf-8',errors='ignore')
    for m in re.finditer(r'Preflight: import fall[oó]|Preflight: import failed',data):
        s=max(0,m.start()-400)
        e=min(len(data),m.end()+400)
        print('--- excerpt ---')
        print(data[s:e])
else:
    print(name,'not found')
