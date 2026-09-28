"""Phone variants in output/m/: 512 px colour / 256 px other maps, no tangents,
one decoded copy per texture. Desktop GLBs keep 1024 px maps (also de-duplicated)."""
import json, hashlib
from pathlib import Path
from glb_util import lite, dedupe_images
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'output'
report = {}
src = OUT / 'surroundings.glb'; blob, n = dedupe_images(src.read_bytes())
if n:
    src.write_bytes(blob)
for rel in ['house.glb', 'surroundings.glb', *[f'styles/{s}.glb' for s in ('bohemian', 'industrial', 'eclectic', 'wabisabi')]]:
    data = (OUT / rel).read_bytes(); small = lite(data)
    dst = OUT / 'm' / rel; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(small)
    report[rel] = dict(desktop_bytes=len(data), phone_bytes=len(small), sha256=hashlib.sha256(small).hexdigest())
(OUT / 'm/mobile-assets.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k: [round(v['desktop_bytes'] / 1e6, 1), round(v['phone_bytes'] / 1e6, 1)] for k, v in report.items()}))
