import zipfile
z=zipfile.ZipFile('site_logs.zip')
for name in z.namelist():
    if 'import_check.log' in name:
        print('FOUND', name)
        print('-' * 80)
        print(z.read(name).decode('utf-8', errors='replace'))
        break
else:
    print('import_check.log not found in site_logs.zip')
