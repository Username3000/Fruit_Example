import unreal
from pathlib import Path
import json
root = Path(unreal.Paths.project_dir()).resolve()
for name in ['SM_Bomb', 'SM_Heart', 'SM_Clock', 'SM_Shuriken']:
    mesh = unreal.load_asset('/Game/Root/Assets/Meshes/Items/' + name)
    b = mesh.get_bounds()
    print(name + ':' + json.dumps({'origin': [b.origin.x, b.origin.y, b.origin.z], 'size': [b.box_extent.x*2, b.box_extent.y*2,b.box_extent.z*2]}))
    try:
        info = mesh.get_editor_property('thumbnail_info')
        print('THUMBNAIL:' + name + ':' + str(info))
        if info:
            print('THUMB_DATA:' + name + ':' + str(info.__class__.__doc__))
    except Exception as e:
        print('THUMBNAIL_ERROR:' + str(e))
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([unreal.load_asset('/Game/Root/Assets/Meshes/Items/SM_Clock')])
