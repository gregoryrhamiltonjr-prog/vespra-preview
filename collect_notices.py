"""Collect installed package notices for the distributed JS bundle; no license clearance claim."""
from pathlib import Path
import json
root=Path(__file__).parent
parts=['VESPRA mobile third-party notices\n\nGenerated from the pinned installed dependency tree. Copyright and licenses remain with their authors. This collection is not legal clearance or a complete license compatibility audit. No third-party font/photo assets are bundled.\n']
count=0
for package in sorted((root/'node_modules').rglob('package.json')):
    try:meta=json.loads(package.read_text())
    except (ValueError,OSError):continue
    if not meta.get('name') or not meta.get('version'):continue
    notices=[p for p in package.parent.iterdir() if p.is_file() and p.name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE'))]
    label=meta['name']+'@'+meta['version']
    parts.append('\n'+'='*72+'\n'+label+'\nDeclared license: '+str(meta.get('license','not declared'))+'\n')
    if notices:
        for notice in notices:
            try:parts.append('\n--- '+notice.name+' ---\n'+notice.read_text(errors='replace'))
            except OSError:pass
    else:parts.append('No standalone root notice found. Consult the package source and declared license before release.\n')
    count+=1
(root/'THIRD_PARTY_NOTICES.txt').write_text('\n'.join(parts))
print(f'Collected notices from {count} installed package manifests. Legal review remains required.')
