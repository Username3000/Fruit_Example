import unreal
import json
from pathlib import Path

root = Path(unreal.Paths.project_dir()).resolve()
base = '/Game/Root/Assets'
# Only remove the unused material instances created during the first GLB import.
for i in range(1, 9):
    path = base + '/Materials/M_Clock_' + str(i).zfill(2)
    asset = unreal.load_asset(path)
    if asset and isinstance(asset, unreal.MaterialInstanceConstant):
        references = unreal.EditorAssetLibrary.find_package_referencers_for_asset(path, load_assets_to_confirm=True)
        if not references:
            assert unreal.EditorAssetLibrary.delete_asset(path)

temporary_folder = base + '/Meshes/Items/timer'
if unreal.EditorAssetLibrary.does_directory_exist(temporary_folder):
    assert not unreal.EditorAssetLibrary.does_directory_have_assets(temporary_folder, recursive=True)
    unreal.EditorAssetLibrary.delete_directory(temporary_folder)

unreal.EditorAssetLibrary.save_directory(base, only_if_is_dirty=True, recursive=True)
exec((root / 'Tools/AssetImport/verify_assets.py').read_text(encoding='utf-8'))
rows = json.loads((root / 'Saved/MCP/asset-verification.json').read_text(encoding='utf-8'))
meshes = [r for r in rows if r['class'] == 'StaticMesh']
assert len(meshes) == 44
assert all(r['collision_count'] > 0 and r['triangles'] > 0 and all(r['materials']) for r in meshes)
assert all(r['path'].startswith(base + '/Meshes/') for r in meshes)
assert all(r['path'].startswith(base + '/Textures/') for r in rows if r['class'] == 'Texture2D')
assert all(r['path'].startswith(base + '/Materials/') for r in rows if r['class'].startswith('Material'))
(root / 'SourceAssets/asset-catalog.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
unreal.EditorAssetLibrary.sync_browser_to_objects([base + '/Meshes/Fruits/SM_Apple', base + '/Meshes/Fruits/SM_Pineapple', base + '/Meshes/Fruits/SM_Watermelon'])
print('FINAL_CHECK:' + json.dumps({'meshes': len(meshes), 'textures': len([r for r in rows if r['class'] == 'Texture2D']), 'all_saved': True}))
