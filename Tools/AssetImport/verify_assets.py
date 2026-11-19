import unreal
import json
from pathlib import Path

root = Path(unreal.Paths.project_dir()).resolve()
base = '/Game/Root/Assets'
editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)

rows = []
for path in unreal.EditorAssetLibrary.list_assets(base, recursive=True):
    asset = unreal.load_asset(path)
    kind = asset.get_class().get_name()
    row = {'path': path, 'class': kind}
    if isinstance(asset, unreal.StaticMesh):
        b = asset.get_bounds()
        row.update({'size_cm': [b.box_extent.x * 2, b.box_extent.y * 2, b.box_extent.z * 2],
                    'collision_count': editor.get_simple_collision_count(asset) + editor.get_convex_collision_count(asset),
                    'materials': [slot.material_interface.get_path_name() if slot.material_interface else None for slot in asset.static_materials]})
        if hasattr(asset, 'get_num_triangles'):
            row['triangles'] = asset.get_num_triangles(0)
    rows.append(row)
(root / 'Saved/MCP/asset-verification.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('VERIFICATION:' + json.dumps({'asset_count': len(rows), 'mesh_count': len([r for r in rows if r['class'] == 'StaticMesh']), 'texture_count': len([r for r in rows if r['class'] == 'Texture2D']), 'zero_collisions': [r['path'] for r in rows if r.get('collision_count') == 0]}))
