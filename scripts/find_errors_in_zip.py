import zipfile
z=zipfile.ZipFile('site_logs.zip')
keywords=['ModuleNotFoundError','Traceback','ImportError','HaltServer','Worker failed to boot']
for name in z.namelist():
    try:
        data=z.read(name).decode('utf-8',errors='ignore')
    except Exception:
        continue
    for kw in keywords:
        if kw in data:
            print('MATCH',kw,'in',name)
            idx=data.find(kw)
            start=max(0,idx-200)
            end=min(len(data),idx+200)
            print(data[start:end])
            print('-'*80)
            break
