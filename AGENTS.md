# Fruit Example

This is an Unreal Engine 5.8 project. Work with Unreal assets and the editor through
the project MCP server `unreal_fruit`. Start with `editor_status` and use its
`list_assets`, `list_level_actors`, `execute_python`, and `save_all` tools.
Only connect to the editor whose project root matches this directory.

If the newly configured server is not yet in the current chat's tool catalog,
use the real MCP stdio client as a temporary fallback:

```powershell
.\Tools\UnrealMCP\.venv\Scripts\python.exe .\Tools\UnrealMCP\client.py editor_status
```

`client.py tools` lists tools; `client.py execute_python --arguments-file <file>`
accepts a UTF-8 JSON object containing `code`. This still goes through MCP.
The project must be open in Unreal Editor. Do not edit binary `.uasset`/`.umap`
files directly. Do not automatically retry a timed-out mutation; inspect the
editor state first. Save intentional edits explicitly.

Setup and local transport details are in `Tools/UnrealMCP/README.md`.

Fruit children live in `/Game/Root/Blueprints/Fruits` and inherit `B_FruitBase`.
The existing `Damage` function calls `SpawnFruitPieces` before destroying the
actor. Read `Tools/FruitSetup/README.md` before changing this setup. Movement
uses the Blueprint's `CurrentVelocity`; `Actor.GetVelocity()` is not equivalent.

UE 5.8 provides `BlueprintGraphEditor` and `BlueprintGraphPinLibrary` for graph
edits through Python/MCP. Lightweight Niagara emitters can be edited through
their nested editable module objects. Keep one module instance per native
class: stateless templates deduplicate module classes when assets load.
Avoid `JsonObjectGraphFunctionLibrary.stringify` on compiled Niagara systems:
the installed engine can crash in `NiagaraEmitterCompiledData` serialization.
Inspect a nested emitter or individual module instead.

The blade trail is owned and rendered by B_FruitPlayerController, using the
same Left Mouse Button Pressed/Released events as its existing slicing Gate.
Read Tools/BladeTrail/README.md before changing it. There is no custom HUD
dependency. Keep blade components collision-free. Recompile a Blueprint after
changing inherited native CDO defaults such as HUDClass so its optimized spawn
property list is refreshed.
