import os
import zipfile

root = os.path.abspath(os.path.dirname(__file__) + os.sep + '..')
zip_path = os.path.join(root, 'deploy_with_projects.zip')
includes = [
    'db',
    'Projects',
    'main.py',
    'startup.sh',
    'install_uvicorn.sh',
    'requirements.txt',
    'app_settings.py',
    'logging_config_new.py',
    'Services',
    'routers'
]

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for item in includes:
        full = os.path.join(root, item)
        if os.path.isdir(full):
            for dirpath, dirnames, filenames in os.walk(full):
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    arcname = os.path.relpath(fpath, root)
                    z.write(fpath, arcname)
        elif os.path.isfile(full):
            z.write(full, item)
        else:
            print(f"Warning: {item} not found, skipping")

print('Created', zip_path)
