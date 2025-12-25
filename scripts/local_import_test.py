try:
    import importlib
    importlib.import_module('main')
    print('Imported OK')
except Exception as e:
    import traceback
    print('Import failed:', e)
    traceback.print_exc()
