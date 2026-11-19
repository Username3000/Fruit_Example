# Fruit game HUD (UMG)

Open `/Game/Root/Blueprints/UI/WBP_FruitHUD` in the UMG Designer.

The editable widget hierarchy is:

- HUDCanvas (Canvas Panel)
  - ScoreText (TextBlock), anchored top left, offset 28,28.
  - TimerText (TextBlock), anchored top right, alignment 1,0, offset -28,28.
  - HealthRow (Horizontal Box), anchored bottom left, alignment 0,1.
    - Three 64x64 Size Boxes containing Heart1, Heart2, Heart3 (Images).

Missing hearts use RenderOpacity 0.30, filled hearts 1.0, left to right.
The image brush uses `M_HUDHeart`, a UI material sampling cell 0 of the existing
`T_ItemEffects_Atlas` with its original alpha crop. No new heart icon was generated.
UMG anchors and project DPI scaling control layout; font, spacing, positions and
sizes are editable in Designer. The HUD is hit-test invisible and leaves slicing
input with the existing player controller.

`WBP_FruitHUD` caches the owning `B_FruitPlayerController` and game mode on
Construct. Its small RefreshHUD function updates the score, time and health via
separate UpdateScore, UpdateTimer and UpdateHealth functions. UpdateHeart handles
the opacity of a single Image. Tick calls RefreshHUD.

`B_FruitHUD` only creates the widget with its owning player, adds it to the
viewport once on BeginPlay and removes it on EndPlay. It has no Canvas draw
functions or ReceiveDrawHUD override. GameMode continues to select B_FruitHUD.
The blade trail stays in B_FruitPlayerController.

Existing gameplay data remains unchanged: controller Score/CurrentHealth/MaxHealth
and DamagePlayer/HealPlayer/AddScore; GameMode RoundDuration=60, RemainingTime,
ResetRoundTimer, TickRoundTimer and GetRoundTimeText. Time is clamped at zero and
formatted as MM:SS. Health is limited to three lives.

`create_hud.py` runs create_widget_tree.py and migrate_to_umg.py through MCP.
These scripts regenerate the HUD layout and its presentation functions; review
manual Designer/graph changes before rerunning. They do not rebuild gameplay
stat functions or the GameMode timer. Previous Canvas HUD backup:
`Saved/Backups/HUD/BeforeUMG/B_FruitHUD.uasset`.

`test_hud.py` runs real PIE and verifies live UMG instances, TextBlock contents,
Image alpha, timer progression/format/zero limit, player stat limits and unchanged
blade component ownership. It captures the UI using Shot -showui, then ends PIE.
Report: `Saved/MCP/hud-checks.json`.
Preview: `Saved/MCP/hud-umg-preview.png`.
