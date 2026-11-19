import unreal
import json
from pathlib import Path

root = Path(unreal.Paths.project_dir()).resolve()
base = '/Game/Root/Assets'
exec((root / 'Tools/AssetImport/import_models.py').read_text(encoding='utf-8'))
editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
asset_editor = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)

def solid(name, color, metallic=0.0, roughness=0.6):
    mat = unreal.load_asset(base + '/Materials/' + name)
    if mat:
        return mat
    mat = asset_tools.create_asset(name, base + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    rgb = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
    rgb.constant = unreal.LinearColor(*color[:3], 1.0)
    unreal.MaterialEditingLibrary.connect_material_property(rgb, '', unreal.MaterialProperty.MP_BASE_COLOR)
    for value, prop, y in [(metallic, unreal.MaterialProperty.MP_METALLIC, 180), (roughness, unreal.MaterialProperty.MP_ROUGHNESS, 300)]:
        expr = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, y)
        expr.r = value
        unreal.MaterialEditingLibrary.connect_material_property(expr, '', prop)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat

heart_mat = solid('M_Heart_Red', (0.65, 0.015, 0.035), roughness=0.5)
bomb_mat = unreal.load_asset(base + '/Materials/M_Bomb')
if True:
    if not bomb_mat:
        bomb_mat = asset_tools.create_asset('M_Bomb', base + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    else:
        unreal.MaterialEditingLibrary.delete_all_material_expressions(bomb_mat)
    sample = unreal.MaterialEditingLibrary.create_material_expression(bomb_mat, unreal.MaterialExpressionTextureSample, -700, 0)
    sample.texture = item_texture
    black = unreal.MaterialEditingLibrary.create_material_expression(bomb_mat, unreal.MaterialExpressionConstant3Vector, -700, 250)
    black.constant = unreal.LinearColor(0.012, 0.017, 0.025, 1)
    fuse = unreal.MaterialEditingLibrary.create_material_expression(bomb_mat, unreal.MaterialExpressionConstant3Vector, -700, 400)
    fuse.constant = unreal.LinearColor(0.5, 0.23, 0.055, 1)
    select = unreal.MaterialEditingLibrary.create_material_expression(bomb_mat, unreal.MaterialExpressionIf, -300, 0)
    pins = list(unreal.MaterialEditingLibrary.get_material_expression_input_names(select))
    print('IF_PINS:' + str(pins))
    for (node, output), pin in zip([(sample, 'R'), (sample, 'B'), (fuse, ''), (black, ''), (black, '')], pins):
        assert unreal.MaterialEditingLibrary.connect_material_expressions(node, output, select, pin)
    unreal.MaterialEditingLibrary.connect_material_property(select, '', unreal.MaterialProperty.MP_BASE_COLOR)
    rough = unreal.MaterialEditingLibrary.create_material_expression(bomb_mat, unreal.MaterialExpressionConstant, -300, 300)
    rough.r = 0.4
    unreal.MaterialEditingLibrary.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    unreal.MaterialEditingLibrary.recompile_material(bomb_mat)
    unreal.EditorAssetLibrary.save_loaded_asset(bomb_mat)

originals = {Path(row['path'].split('.')[0]).name: row for row in json.loads((root / 'Saved/MCP/asset-import-report.json').read_text())}
def replace_mesh(filename, name, target, material=None, is_obj=False):
    path = base + '/Meshes/Items/' + name
    old = unreal.load_asset(path)
    asset_editor.close_all_editors_for_asset(old)
    references = list(unreal.EditorAssetLibrary.find_package_referencers_for_asset(path, load_assets_to_confirm=True))
    assert not references, 'Preserve referenced asset: ' + path + ':' + str(references)
    assert unreal.EditorAssetLibrary.delete_asset(path)
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal = False
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.import_mesh = True
    options.is_obj_import = is_obj
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = True
    data.build_nanite = False
    data.convert_scene = True
    data.convert_scene_unit = True
    data.generate_lightmap_u_vs = True
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS if is_obj else unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.import_uniform_scale = 1.0 if is_obj else target / max(originals[name]['size_cm'])
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_name = name
    task.destination_path = base + '/Meshes/Items'
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = options
    task.factory = unreal.FbxFactory()
    task.save = True
    asset_tools.import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    assert isinstance(mesh, unreal.StaticMesh)
    if material:
        for slot in range(len(mesh.static_materials)):
            mesh.set_material(slot, material)
    editor.remove_collisions(mesh)
    assert editor.add_simple_collisions(mesh, unreal.ScriptingCollisionShapeType.NDOP26) >= 0
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    print('REPLACED:' + name + ':' + str(mesh.get_bounds()))
    return mesh

replace_mesh(source / 'Kenney_platformer_kit/Models/FBX format/bomb.fbx', 'SM_Bomb', 30, bomb_mat)
replace_mesh(source / 'Kenney_platformer_kit/Models/FBX format/heart.fbx', 'SM_Heart', 24, heart_mat)
steel = unreal.load_asset(base + '/Materials/M_Shuriken_Steel')
for source_name, name in [('shuriken', 'SM_Shuriken'), ('shiho', 'SM_Shuriken_FourPoint'), ('happo', 'SM_Shuriken_EightPoint')]:
    replace_mesh(source / 'Shuriken/dist/fbx' / (source_name + '.fbx'), name, 20, steel)
clock = replace_mesh(source / 'Timer/clock.obj', 'SM_Clock', 28, is_obj=True)
colors = json.loads((source / 'Timer/materials.json').read_text())
for index, slot in enumerate(clock.static_materials):
    slot_name = str(slot.material_slot_name)
    print('CLOCK_SLOT:' + slot_name)
    material_index = int(slot_name.rsplit('_', 1)[-1]) - 1
    pbr = colors[material_index]['pbrMetallicRoughness']
    mat = solid('M_Clock_' + str(material_index + 1).zfill(2) + '_Color', pbr['baseColorFactor'], pbr['metallicFactor'], 0.5)
    clock.set_material(index, mat)
unreal.EditorAssetLibrary.save_loaded_asset(clock)
unreal.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 1')
exec((root / 'Tools/AssetImport/verify_assets.py').read_text(encoding='utf-8'))
for name, target in [('SM_Clock',28),('SM_Bomb',30),('SM_Heart',24),('SM_Shuriken',20),('SM_Shuriken_FourPoint',20),('SM_Shuriken_EightPoint',20)]:
    mesh = unreal.load_asset(base + '/Meshes/Items/' + name)
    b = mesh.get_bounds()
    assert abs(max(b.box_extent.x, b.box_extent.y, b.box_extent.z)*2 - target) < 0.1, name + ' has unexpected bounds'
print('POLISH_COMPLETE')
unreal.EditorAssetLibrary.sync_browser_to_objects([base + '/Meshes/Items/SM_Bomb', base + '/Meshes/Items/SM_Heart', base + '/Meshes/Items/SM_Clock'])
