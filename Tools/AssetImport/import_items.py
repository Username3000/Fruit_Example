import unreal
import json
from pathlib import Path

root = Path(unreal.Paths.project_dir()).resolve()
exec((root / 'Tools/AssetImport/import_models.py').read_text(encoding='utf-8'))

def solid_material(name, color, metallic=0.0, roughness=0.55):
    existing = unreal.load_asset(base + '/Materials/' + name)
    if existing:
        return existing
    mat = asset_tools.create_asset(name, base + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    rgb = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
    rgb.constant = unreal.LinearColor(*color, 1.0)
    unreal.MaterialEditingLibrary.connect_material_property(rgb, '', unreal.MaterialProperty.MP_BASE_COLOR)
    for value, prop, y in [(metallic, unreal.MaterialProperty.MP_METALLIC, 200), (roughness, unreal.MaterialProperty.MP_ROUGHNESS, 350)]:
        expr = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, y)
        expr.r = value
        unreal.MaterialEditingLibrary.connect_material_property(expr, '', prop)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat

steel = solid_material('M_Shuriken_Steel', (0.23, 0.28, 0.34), 0.75, 0.35)
for source_name, name in [('shuriken', 'SM_Shuriken'), ('shiho', 'SM_Shuriken_FourPoint'), ('happo', 'SM_Shuriken_EightPoint')]:
    mesh = import_fbx(source / 'Shuriken/dist/fbx' / (source_name + '.fbx'), name, 'Items')
    for slot in range(len(mesh.static_materials)):
        mesh.set_material(slot, steel)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    record(mesh, 'Items', '3D Shuriken Pack / mehrasaur')

clock = unreal.load_asset(base + '/Meshes/Items/SM_Clock')
if not clock:
    task = unreal.AssetImportTask()
    task.filename = str(source / 'Timer/timer.glb')
    task.destination_path = base + '/Meshes/Items'
    task.automated = True
    task.save = True
    task.replace_existing = False
    asset_tools.import_asset_tasks([task])
    imported = list(task.get_objects())
    clocks = [obj for obj in imported if isinstance(obj, unreal.StaticMesh)]
    assert len(clocks) == 1, 'Expected one clock mesh, got ' + str(len(clocks))
    clock = clocks[0]
    if clock.get_name() != 'SM_Clock':
        assert unreal.EditorAssetLibrary.rename_asset(clock.get_path_name(), base + '/Meshes/Items/SM_Clock')
        clock = unreal.load_asset(base + '/Meshes/Items/SM_Clock')
    for i, slot in enumerate(clock.static_materials):
        mat = slot.material_interface
        if mat and mat.get_path_name().startswith(base + '/Meshes/'):
            target = base + '/Materials/M_Clock_' + str(i + 1).zfill(2)
            assert unreal.EditorAssetLibrary.rename_asset(mat.get_path_name(), target)
    editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    if editor.get_simple_collision_count(clock) == 0:
        editor.add_simple_collisions(clock, unreal.ScriptingCollisionShapeType.NDOP26)
    settings = clock.get_editor_property('nanite_settings')
    settings.enabled = False
    clock.set_editor_property('nanite_settings', settings)
    unreal.EditorAssetLibrary.save_loaded_asset(clock)
    record(clock, 'Items', 'Timer / scaranto / Poly Pizza')

# Save only this task's asset directory, preserving unrelated editor work.
unreal.EditorAssetLibrary.save_directory(base, only_if_is_dirty=True, recursive=True)
unreal.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 1')
print('ITEMS_COMPLETE:' + json.dumps({'total_models': len(report)}))
