# Fruit blueprints and Niagara pieces

Heart, Clock and Bomb children and effects are documented in `ITEMS.md`.

Created eight children of `/Game/Root/Blueprints/B_FruitBase` in
`/Game/Root/Blueprints/Fruits`:

`B_Fruit_Apple`, `B_Fruit_Banana`, `B_Fruit_Coconut`, `B_Fruit_Orange`,
`B_Fruit_Pear`, `B_Fruit_Pineapple`, `B_Fruit_Strawberry`, `B_Fruit_Watermelon`.

Each child overrides the inherited `Mesh` component and the `FruitBurstSystem`
class default. Their mesh scale is 2.5 on all axes. Existing movement and gravity remain inherited.

The base `Damage` function calls `SpawnFruitPieces` before its existing
`Destroy Actor`. The burst spawns at the mesh bounds center, detached from
the fruit. Auto activation is disabled while the Blueprint sets
`User.InheritedVelocity` from the existing **CurrentVelocity** variable, then
the Niagara component is activated. Actor velocity is deliberately not used:
this project moves fruit with manual world offsets.

Each `NS_FruitPieces_*` system in `/Game/Root/Assets/VFX/Fruits` uses an editable
lightweight Niagara sprite emitter. It emits 3 pieces with lifetime 2.2–4.2 s,
random rotation, spin, initial position scatter and random outward acceleration.
A linear velocity module copies the fruit's actual world velocity. The system
spawns with identity rotation and scale, so emitter and world vector axes agree;
gravity and the random forces bend the trajectories afterward.
The detached component completes and destroys itself independently of the fruit.
Pieces initially appear in a sphere of radius 40 cm around the burst center.
The base function calculates the mesh's full size along camera right/up from
its actual world bounds, including actor and component scale. It sends 70% of
the larger dimension as `User.PieceSize` (Vector2) before activating Niagara.
Initialize Particle binds to this parameter. Template sprite size scaling
modules are disabled to preserve the initialized size, except pineapple:
its Scale Sprite Size module multiplies both axes by 0.5, giving 35% of the
model size instead of 70%. Other fruits retain their existing sizes.

Fruit children opt into gentle mesh rotation through `FruitVisualRotationEnabled`.
`InitializeFruitVisualRotation` records the existing mesh-relative pose, then
adds up to 2 degrees per axis once. `TickFruitVisualRotation` adds smooth,
bounded 6-degree sine sway over flight, using DeltaSeconds. It does not change
the launch transform, CurrentVelocity or gravity. Items default to disabled.
The base captures the actual spawn pose, so authored orientations are preserved.
`add_visual_motion.py` authors this setup. `start_visual_motion_test.py` starts
its short PIE test on the first play frame; the test checks all eight fruits,
unchanged flight, an unchanged heart, and live half-sized pineapple sprites.

The shared masked, Default Lit, two-sided `M_FruitChunks` uses the generated 4 × 4
atlas and its alpha. Each system uses a material instance with its own
`FruitIndex`. The material combines this with stable `ParticleRandom` to select
one of that fruit's two cells; sprites do not animate into other fruits. Generation details
and the exact prompt are in `SourceAssets/FruitVFX/generation.md`.
Each cell is cropped in the material using its alpha silhouette bounds, with
two pixels of filtering margin. This gives both variants approximately the
same visible size instead of measuring the transparent sprite quad. Calibration
data is in `SourceAssets/FruitVFX/chunk_uv_bounds.json`. Sprite spin and perspective
can change the apparent bounding width during flight.
Fruit particles use Base Color with zero emissive, roughness 0.8 and specular
0.2, so they respond to scene lighting. Heart and clock pieces use the same
lighting settings through M_ItemPieces; the bomb materials stay Unlit.

These blueprints can now be put in the launcher's spawn collection. The
existing launcher's selection logic has not been changed by this task.

## Editing and verification

All Unreal asset edits were executed through MCP using
`Tools/UnrealMCP/run_script.py`. `create_vfx.py` builds the effects;
`create_blueprints.py` builds the base graph and children. The latter regenerates
the `SpawnFruitPieces` graph, so review manual changes there before rerunning it.
`proportion_pieces.py` applies the current atlas calibration, dynamic size
binding, and lifetime settings; creation and legacy resize scripts invoke it
after their own edits. Notify the owning emitter after changing nested modules
to refresh its runtime data, rather than relying on saved property values alone.

`validate_setup.py` checks inheritance, references and graph compilation.
`test_runtime_async.py` runs in PIE, damages each fruit, captures live Niagara
simulation data, checks sprite frames and movement direction in both X
directions, checks actual live sprite sizes against the 70% binding (including
an actor scaled by 2), checks survival after 1.7 seconds, and verifies automatic
completion. It ends PIE when finished.
Reports are saved in `Saved/MCP/fruit-static-checks.json` and
`Saved/MCP/fruit-runtime-checks.json`.

The original base Blueprint was backed up to
`Saved/Backups/FruitSetup/B_FruitBase.before-fragments.uasset` before graph edits.
