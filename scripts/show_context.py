from pathlib import Path
import re
s = Path('Projects/ecomerce/templates/producto_detalle.html').read_text(encoding='utf-8')
scripts = list(re.finditer(r"<script[^>]*>([\s\S]*?)</script>", s, flags=re.I))
script = scripts[2].group(1)
# Problem try index 31948
for i in [31948]:
    start = max(0, i-200)
    end = min(len(script), i+400)
    context = script[start:end]
    file_start = scripts[2].start(1)
    line_before = s[:file_start+start].count('\n')+1
    print('File line approx:', line_before)
    print('---context---')
    print(context)
    print('---end---')
