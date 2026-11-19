# Mouse capture with a visible cursor

`B_FruitHUD.ShowHUDWidget` keeps `Set Input Mode Game Only`, followed immediately
by `Set Viewport Mouse Capture Mode` = `Capture Permanently Including Initial Mouse Down`.
Always apply the capture override **after** Game Only, including when returning
from the end-game screen.

UE 5.8's `UWidgetBlueprintLibrary::SetInputMode_GameOnly` constructs an
`FInputModeGameOnly` whose `bConsumeCaptureMouseDown` defaults to true.
`FInputModeGameOnly::ApplyInputMode` therefore changes the viewport capture mode
to `CapturePermanently`, replacing the project's configured
`CapturePermanently_IncludingInitialMouseDown`.

With this controller's `ShowMouseCursor = true`,
`FSceneViewport::OnMouseButtonUp` releases mouse capture. The next
`OnMouseButtonDown` in `CapturePermanently` restores capture but skips sending
`IE_Pressed` to the game. `IE_Released` still arrives. Including the initial mouse
down fixes this while retaining Game Only and the visible cursor.

Local engine source: `Engine/Source/Runtime/UMG/Private/WidgetBlueprintLibrary.cpp`
(`SetInputMode_GameOnly`), `Engine/Source/Runtime/Engine/Private/PlayerController.cpp`
(`FInputModeGameOnly`), and `Engine/Source/Runtime/Engine/Private/Slate/SceneViewport.cpp`
(`OnMouseButtonDown`, `OnMouseButtonUp`).

The change was authored through Unreal MCP; `fix_mouse_capture.py` documents it.
It deliberately refuses to run twice. The original saved HUD is backed up in
`Saved/Backups/MouseInput/B_FruitHUD.before-capture-fix.uasset`.

PIE validation used real Windows mouse drags and Unreal MCP observation, without
direct calls to Begin/EndBladeStroke. Before the fix the controller printed only
RELEASED for repeat clicks. Changing capture mode alone restored PRESSED/RELEASED.
A fresh PIE run of the saved Blueprint received three complete pairs, including
after calling ShowHUDWidget again. Release left BladeHeld false, zero visible
segments and no trail samples. HUD compilation had zero errors and warnings.

Reports: `Saved/MCP/mouse-input-before-and-runtime-fix.json` and
`Saved/MCP/mouse-input-fixed.json`. The latter includes the controller's existing
PrintString log evidence; a short click may press and release within one frame,
so per-frame polling alone can miss it. These short automated drags did not
verify the rendered trail's shape or fruit slicing.

For another interactive test, execute `observe_mouse_input.py` through MCP while
PIE is stopped, send actual viewport drags, then call `finish_mouse_input_test()`
through MCP. The observer temporarily disables the PIE GameMode timer tick, writes
the observations and ends PIE. It makes no saved gameplay changes.
