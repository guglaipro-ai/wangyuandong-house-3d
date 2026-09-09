from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
root=Path(__file__).resolve().parents[1]/'output'
with ZipFile(root/'王源東住宅3D模型.zip','w',ZIP_DEFLATED) as archive:
    for file in sorted(root.rglob('*')):
        if file.is_file() and file.suffix!='.zip':archive.write(file,file.relative_to(root))
print('Delivery archive updated')
