"""Tune existing fruit bursts through MCP without changing fruit Blueprints."""
import json
from pathlib import Path
import unreal

assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'End PIE before editing effects'
report = []
for fruit in ['Apple', 'Banana', 'Coconut', 'Orange', 'Pear', 'Pineapple', 'Strawberry', 'Watermelon']:
    system = unreal.load_asset('/Game/Root/Assets/VFX/Fruits/NS_FruitPieces_' + fruit)
    emitter = unreal.find_object(system, 'DirectionalBurst_1')
    modules = list(emitter.get_editor_property('Modules'))
    init = next(m for m in modules if m.get_class().get_name() == 'NiagaraStatelessModule_InitializeParticle')
    shape = next(m for m in modules if m.get_class().get_name() == 'NiagaraStatelessModule_ShapeLocation')
    system.modify()
    emitter.modify()
    init.modify()
    shape.modify()
    maximum = 88 if fruit in ['Coconut', 'Pineapple', 'Watermelon'] else 64
    minimum = maximum * 0.65
    size = init.get_editor_property('SpriteSizeDistribution').copy()
    assert size.import_text(f'(Min=(X={minimum},Y={minimum}),Max=(X={maximum},Y={maximum}),Mode=UniformRange,ChannelConstantsAndRanges=({minimum},{maximum}))')
    init.set_editor_property('SpriteSizeDistribution', size)
    spawn = emitter.get_editor_property('SpawnInfos')[0].copy()
    assert spawn.import_text('(Type=Burst,SpawnTime=0,Amount=(Min=3,Max=3,Mode=UniformConstant),bEnabled=True)')
    emitter.set_editor_property('SpawnInfos', [spawn])
    radius = shape.get_editor_property('SphereRadius').copy()
    assert radius.import_text('(Min=40,Max=40,Mode=UniformConstant,ChannelConstantsAndRanges=(40))')
    shape.set_editor_property('SphereRadius', radius)
    shape.set_editor_property('bModuleEnabled', True)
    assert unreal.EditorAssetLibrary.save_loaded_asset(system)
    actual_size = init.get_editor_property('SpriteSizeDistribution')
    for key, expected in [('Min', minimum), ('Max', maximum)]:
        vector = actual_size.get_editor_property(key)
        assert all(abs(vector.get_editor_property(axis) - expected) < 0.01 for axis in ['X', 'Y'])
    amount = emitter.get_editor_property('SpawnInfos')[0].get_editor_property('Amount')
    assert amount.get_editor_property('Min') == 3 and amount.get_editor_property('Max') == 3
    radius = shape.get_editor_property('SphereRadius')
    assert radius.get_editor_property('Min') == 40 and radius.get_editor_property('Max') == 40
    report.append({'fruit': fruit, 'piece_size_cm': [minimum, maximum], 'piece_count': 3, 'spawn_radius_cm': 40})
    print('TUNED:' + json.dumps(report[-1]))
(Path(unreal.Paths.project_dir())/'Saved/MCP/fruit-piece-adjustment.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('FRUIT_PIECES_SAVED:' + str(len(report)))
calibration=Path(unreal.Paths.project_dir())/'Tools/FruitSetup/proportion_pieces.py'
exec(compile(calibration.read_text(encoding='utf-8'),str(calibration),'exec'),{'__name__':'__main__'})
