import unreal
import json

assets = unreal.EditorAssetLibrary.list_assets('/Game/Root/Assets', recursive=True)
print('CURRENT_ASSETS:' + json.dumps(list(assets)))
for name in ['FbxImportUI', 'FbxStaticMeshImportData', 'StaticMeshEditorSubsystem', 'EditorAssetLibrary', 'AssetImportTask']:
    cls = getattr(unreal, name)
    print('API:' + name + ':' + str(cls.__doc__)[:8000])
