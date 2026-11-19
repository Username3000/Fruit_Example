import unreal
import json
from pathlib import Path

root = Path(unreal.Paths.project_dir()).resolve()
base = '/Game/Root/Assets'
editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
targets = {'SM_Clock': 28.0, 'SM_Heart': 24.0, 'SM_Bomb': 30.0, 'SM_Shuriken': 20.0,
           'SM_Shuriken_FourPoint': 20.0, 'SM_Shuriken_EightPoint': 20.0}
for name, target in targets.items():
    mesh = unreal.load_asset(base + '/Meshes/Items/' + name)
    assert mesh is not None
    bounds = mesh.get_bounds()
    longest = max(bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z) * 2
    if abs(longest - target) > 0.02:
        build = editor.get_lod_build_settings(mesh, 0)
        old = build.build_scale3d
        factor = target / longest
        build.build_scale3d = unreal.Vector(old.x * factor, old.y * factor, old.z * factor)
        editor.set_lod_build_settings(mesh, 0, build)
        editor.remove_collisions(mesh)
        assert editor.add_simple_collisions(mesh, unreal.ScriptingCollisionShapeType.NDOP26) >= 0
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)

for path in unreal.EditorAssetLibrary.list_assets(base, recursive=True):
    asset = unreal.load_asset(path)
    if isinstance(asset, unreal.StaticMesh):
        count = editor.get_simple_collision_count(asset) + editor.get_convex_collision_count(asset)
        if not count:
            assert editor.add_simple_collisions(asset, unreal.ScriptingCollisionShapeType.NDOP26) >= 0
            unreal.EditorAssetLibrary.save_loaded_asset(asset)

unreal.EditorAssetLibrary.save_directory(base, only_if_is_dirty=True, recursive=True)
exec((root / 'Tools/AssetImport/verify_assets.py').read_text(encoding='utf-8'))
rows = json.loads((root / 'Saved/MCP/asset-verification.json').read_text())
meshes = [row for row in rows if row['class'] == 'StaticMesh']
assert len(meshes) == 44
assert all(row['collision_count'] > 0 for row in meshes)
assert all(row['triangles'] > 0 and all(row['materials']) for row in meshes)
for row in rows:
    if row['class'] == 'StaticMesh':
        assert row['path'].startswith(base + '/Meshes/')
    elif row['class'] == 'Texture2D':
        assert row['path'].startswith(base + '/Textures/')
    elif row['class'].startswith('Material'):
        assert row['path'].startswith(base + '/Materials/')
print('ASSETS_READY:' + json.dumps({'models':len(meshes), 'triangles_min':min(row['triangles'] for row in meshes), 'triangles_max':max(row['triangles'] for row in meshes), 'all_collisions':True}))
unreal.EditorAssetLibrary.sync_browser_to_objects([base + '/Meshes/Items/SM_Bomb', base + '/Meshes/Items/SM_Heart', base + '/Meshes/Items/SM_Clock', base + '/Meshes/Items/SM_Shuriken'])
