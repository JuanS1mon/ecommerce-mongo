import zipfile,re
z=zipfile.ZipFile('site_logs.zip')
name='LogFiles/2025_12_25_lw1sdlwk0001LW_default_docker.log'
if name in z.namelist():
    data=z.read(name).decode('utf-8',errors='ignore')
    for m in re.finditer(r'Traceback \(most recent call last\):', data):
        s=max(0,m.start()-200)
        e=min(len(data),m.end()+800)
        print('--- TRACEBACK EXCERPT ---')
        print(data[s:e])
else:
    print('no file')
