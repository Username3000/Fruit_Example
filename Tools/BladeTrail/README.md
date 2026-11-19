# Controller-owned blade trail

The trail lives in `/Game/Root/Blueprints/Base/B_FruitPlayerController`.
The existing Left Mouse Button event controls both the trail and slicing:

- Pressed -> BeginBladeStroke -> existing Gate.Open.
- Released -> EndBladeStroke -> existing Gate.Close.
- Tick -> TickBladeTrail -> existing Gate.Enter.

The original Gate.Exit -> cursor hit -> B_FruitBase cast -> fruit-hit call is
preserved. Release immediately hides the effect and clears history. A new
press starts a clean stroke. Moving without holding adds no points.

Controller functions own input state, a 64-sample screen-pixel/time ring buffer,
projection and rendering. The controller creates 64 reusable StaticMeshComponents
using the built-in Plane mesh. They have no collision, overlaps or shadows and
are destroyed with their owner. No custom HUD, Widget or trail Actor is needed;
B_FruitGameMode now uses the separate `UI/B_FruitHUD` for score, time and lives;
that HUD has no blade-trail responsibilities (see `Tools/HUD/README.md`).

Segments are deprojected onto a camera-parallel plane. Each uses a dynamic
instance of M_BladeTrail (white core / cyan halo, additive, no depth test).
Local mesh coordinates pass through a vertex interpolator to the pixel shader.
Width and fade taper with age. Old endpoints are clipped within long sample
intervals to preserve visible swipes at low FPS.

Controller defaults under Blade Trail:

- TrailLifetime: 0.2 seconds.
- TrailWidth: 34 pixels across the outer halo.
- MinPointDistance: 1.5 pixels between samples.

create_trail.py delegates to migrate_controller.py. Only owned trail functions
are regenerated. Original slicing nodes are retained. The editor auto-cast
preference is temporarily used to insert one regular pure cast and immediately
restored. Backups of the controller, original HUD and GameMode are in
Saved/Backups/BladeTrail.

test_controller_async.py (also test_motion_async.py) checks the configured game HUD, component
ownership/collision, screen projection, unheld movement, held movement,
stationary fade, release cleanup and a fresh stroke. It invokes the same Begin/End
functions wired to LMB, moves the real viewport cursor, captures a screenshot,
restores the cursor and ends PIE. finalize.py saves the owned changed assets.
Reports: Saved/MCP/blade-controller-*.json.
