from pathlib import Path
import re
s = Path('Projects/ecomerce/templates/producto_detalle.html').read_text(encoding='utf-8')
# find the toggleWishlist function
m = re.search(r"async function toggleWishlist\([\s\S]*?\n}\n", s)
if not m:
    # try more permissive
    m = re.search(r"async function toggleWishlist\([\s\S]*?\n\}\n\s*// Show notification", s)
if not m:
    print('toggleWishlist not found')
    exit(1)
func = m.group(0)
lines = func.splitlines()
depth = 0
for i, line in enumerate(lines, start=1):
    open_count = line.count('{')
    close_count = line.count('}')
    depth += open_count - close_count
    print(f'{i:03d} depth={depth:3d} | {line}')

print('\nFinal depth:', depth)
