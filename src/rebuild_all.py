"""Rebuild every deliverable in dependency order with the bundled runtimes.
house (untextured) -> architecture baseline copy -> four schemes -> PBR textures -> viewer."""
import subprocess, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; SRC = ROOT / 'src'
PY = sys.executable
NODE = r'C:\Users\t88510\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
def run(*cmd, cwd=SRC):
    print('>', ' '.join(map(str, cmd)), flush=True); subprocess.run(cmd, cwd=cwd, check=True)
run(PY, 'procedural_textures.py')
run(PY, 'build_house.py')
shutil.copy2(ROOT / 'output/house.glb', ROOT / 'output/realism/architecture-baseline.glb')
run(PY, 'build_styles.py')
run(PY, 'enhance_glb.py')
run(PY, 'build_mobile.py')
run(NODE, 'src/package_viewer.mjs', cwd=ROOT)
