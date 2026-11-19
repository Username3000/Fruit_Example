# Item Blueprints and damage effects

`/Game/Root/Blueprints/Items` contains three direct children of `B_FruitBase`:

- `B_Item_Heart`: `SM_Heart`, 7 small whole heart sprites, 2.8–4.2 seconds.
- `B_Item_Clock`: `SM_Clock`, 4 clock dial/cog fragments, 2.2–4.2 seconds.
- `B_Item_Bomb`: `SM_Bomb`, a five-layer stylized explosion.

Each inherited Mesh uses scale 2.5 and its own mesh materials. Heart and Clock
use the base Damage → SpawnFruitPieces → Destroy Actor flow. They copy the
existing `CurrentVelocity` and receive dynamic camera-plane sizing from the
base function. Hearts are 22–31% of the model's camera-plane size; clock
pieces are 56–74%. Both atlas variants have individually calibrated UV crops.

Bomb overrides only `SpawnFruitPieces`, preserving inherited Damage and
movement. Its graph spawns five independent systems at the mesh bounds center,
sets `User.PieceSize` before activation, and uses radial scatter rather than
projectile velocity. Every layer is detached and automatically destroys itself:

| System | Count | Lifetime | Behavior |
| --- | ---: | --- | --- |
| `NS_BombFlash` | 1 | 0.12–0.18 s | Large bright initial flash |
| `NS_BombFire` | 8 | 0.4–0.8 s | Outward moving expanding fire puffs |
| `NS_BombSmoke` | 6 | 1.8–3.2 s | Rising expanding smoke |
| `NS_BombShockwave` | 1 | 0.3–0.45 s | Quickly expanding fiery ring |
| `NS_BombSparks` | 12 | 0.55–1 s | Fast scattered sparks with gravity |

Effects: `/Game/Root/Assets/VFX/Items`. Materials:
`/Game/Root/Assets/Materials/ItemEffects`. Texture:
`/Game/Root/Assets/Textures/T_ItemEffects_Atlas`.

The generated RGBA source, exact prompt, and crop measurements are in
`SourceAssets/ItemVFX`. The material preserves source alpha, suppresses alpha
edge speckles, and fades over normalized particle age. Hearts and clock pieces
are masked/Default Lit with zero emissive; flash/fire/ring/sparks remain
additive/Unlit, and smoke remains translucent/Unlit.

`create_items.py` authors these assets through MCP. It updates the stateless
emitter cache and requests compilation of duplicated Niagara system scripts.
After compilation, save only the intentional item assets. `test_items_async.py`
runs in PIE and checks actual damage dispatch, particle counts and sizes,
inherited motion, all five bomb layers, smoke expansion, automatic completion,
and an existing apple as a regression check. It ends PIE when finished and
writes `Saved/MCP/item-runtime-checks.json`.

`preview_items.py` renders temporary PIE-only model/effect comparisons to
`Saved/MCP/ItemPreviews`; `save_items.py` saves only the item assets after compilation.
