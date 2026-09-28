from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
root=Path(__file__).resolve().parents[1]/'output'
with ZipFile(root/'王源東住宅3D模型.zip','w',ZIP_DEFLATED) as archive:
    for file in sorted(root.rglob('*')):
        if file.is_file() and file.suffix!='.zip' and file.relative_to(root).parts[0]!='m':archive.write(file,file.relative_to(root))
print('Delivery archive updated',round((root/'王源東住宅3D模型.zip').stat().st_size/2**20,1),'MiB (phone assets in m/ are online-only)')
