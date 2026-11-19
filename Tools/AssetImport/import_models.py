"""Run inside Unreal Editor via Tools/UnrealMCP/run_script.py."""
import unreal
import json
from pathlib import Path

root = Path(unreal.Paths.project_dir()).resolve()
source = root / 'SourceAssets'
base = '/Game/Root/Assets'
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
for folder in ['Meshes/Fruits', 'Meshes/Vegetables', 'Meshes/Items', 'Textures', 'Materials']:
    unreal.EditorAssetLibrary.make_directory(base + '/' + folder)

# Force the FBX factory, so its explicit import settings are respected in UE 5.8.
unreal.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')

def import_fbx(filename, name, folder, scale=1.0):
    dest = base + '/Meshes/' + folder
    existing = unreal.load_asset(dest + '/' + name)
    if existing:
        return existing
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal = False
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.import_mesh = True
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = True
    data.build_nanite = False
    data.generate_lightmap_u_vs = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = scale
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = True
    task.options = options
    task.factory = unreal.FbxFactory()
    asset_tools.import_asset_tasks([task])
    meshes = [obj for obj in task.get_objects() if isinstance(obj, unreal.StaticMesh)]
    assert len(meshes) == 1, 'Expected one mesh: ' + str(filename)
    return meshes[0]

def texture(filename, name):
    existing = unreal.load_asset(base + '/Textures/' + name)
    if existing:
        return existing
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = base + '/Textures'
    task.destination_name = name
    task.automated = True
    task.save = True
    asset_tools.import_asset_tasks([task])
    result = next(obj for obj in task.get_objects() if isinstance(obj, unreal.Texture2D))
    result.set_editor_property('filter', unreal.TextureFilter.TF_NEAREST)
    unreal.EditorAssetLibrary.save_loaded_asset(result)
    return result

def palette_material(name, tex):
    existing = unreal.load_asset(base + '/Materials/' + name)
    if existing:
        return existing
    mat = asset_tools.create_asset(name, base + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    sample = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -350, 0)
    sample.texture = tex
    unreal.MaterialEditingLibrary.connect_material_property(sample, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    roughness = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant, -350, 200)
    roughness.r = 0.7
    unreal.MaterialEditingLibrary.connect_material_property(roughness, '', unreal.MaterialProperty.MP_ROUGHNESS)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat

food_texture = texture(source / 'Kenney_food_kit/Models/FBX format/Textures/colormap.png', 'T_Food_ColorMap')
food_material = palette_material('M_Food', food_texture)
item_texture = texture(source / 'Kenney_platformer_kit/Models/FBX format/Textures/colormap.png', 'T_Items_ColorMap')
item_material = palette_material('M_Items', item_texture)

fruits = ['apple', 'apple-half', 'avocado', 'advocado-half', 'banana', 'cherries', 'coconut', 'coconut-half', 'grapes', 'lemon', 'lemon-half', 'orange', 'pear', 'pear-half', 'pineapple', 'strawberry', 'watermelon']
vegetables = ['beet', 'broccoli', 'cabbage', 'carrot', 'cauliflower', 'celery-stick', 'corn', 'eggplant', 'leek', 'mushroom', 'mushroom-half', 'onion', 'onion-half', 'paprika', 'paprika-slice', 'pepper', 'pumpkin', 'pumpkin-basic', 'radish', 'tomato', 'tomato-slice']

report_path = root / 'Saved/MCP/asset-import-report.json'
report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else []
known = {row['path'] for row in report}

def record(mesh, category, source_name):
    if mesh.get_path_name() in known:
        return
    bounds = mesh.get_bounds()
    row = {'path': mesh.get_path_name(), 'category': category, 'source': source_name,
           'size_cm': [bounds.box_extent.x * 2, bounds.box_extent.y * 2, bounds.box_extent.z * 2],
           'material_slots': len(mesh.static_materials)}
    report.append(row)
    known.add(row['path'])
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('IMPORTED:' + json.dumps(row))

# A small batch per MCP request keeps the editor responsive and avoids timeouts.
manifest = []
for category, names in [('Fruits', fruits), ('Vegetables', vegetables)]:
    for name in names:
        nice_name = 'Avocado_Half' if name == 'advocado-half' else '_'.join(part.title() for part in name.split('-'))
        manifest.append((source / 'Kenney_food_kit/Models/FBX format' / (name + '.fbx'), 'SM_' + nice_name, category, food_material, 'Kenney Food Kit'))
for name in ['heart', 'bomb']:
    manifest.append((source / 'Kenney_platformer_kit/Models/FBX format' / (name + '.fbx'), 'SM_' + name.title(), 'Items', item_material, 'Kenney Platformer Kit'))

pending = [entry for entry in manifest if not unreal.EditorAssetLibrary.does_asset_exist(base + '/Meshes/' + entry[2] + '/' + entry[1])]
for filename, name, category, material, origin in pending[:8]:
    mesh = import_fbx(filename, name, category)
    for slot in range(len(mesh.static_materials)):
        mesh.set_material(slot, material)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    record(mesh, category, origin)
print('BATCH_STATUS:' + json.dumps({'imported_total': len(report), 'remaining': max(0, len(pending) - 8)}))
