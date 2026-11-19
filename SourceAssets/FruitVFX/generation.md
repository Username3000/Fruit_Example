# Fruit chunk atlas

Generated with the built-in **imagegen** tool, with `transparent_background=true`.
The supplied Content Browser screenshot was used as a style/color reference.
Final source: `T_FruitChunks_Atlas.png` (RGBA, 1254 × 1254 pixels).
Imported texture: `/Game/Root/Assets/Textures/T_FruitChunks_Atlas`.
The generated alpha is preserved; the masked particle material clips low-alpha
edge pixels at 0.5. No separate image-editing process was used.

The atlas has 4 × 4 cells. Every fruit has two variations:

| Fruit | Zero-based frame indices |
|---|---|
| Apple | 0–1 |
| Banana | 2–3 |
| Coconut | 4–5 |
| Orange | 6–7 |
| Pear | 8–9 |
| Pineapple | 10–11 |
| Strawberry | 12–13 |
| Watermelon | 14–15 |

## Exact generation prompt

Create ONE production game VFX SPRITE ATLAS on genuinely transparent alpha background, square 2048x2048. Reference image is STYLE/COLOR reference only: simple colorful low-poly Kenney fruit models. Exactly 4 columns by 4 rows, 16 evenly spaced square cells, NO grid lines, NO labels, NO text. One single isolated small broken FRUIT CHUNK per cell, centered in its own cell, max 65% cell size with ample transparent padding, nothing crossing cell borders. Orthographic three-quarter view, chunky angular flat-shaded low-poly geometry, clean sharp silhouette, soft simple diffuse shading, no cast shadows, no glow, no whole fruits, no splash clouds, no background. Read order left to right top to bottom MUST be: row1 two different APPLE fragments (coral red peel, pale cream flesh), then two BANANA fragments (yellow peel with ivory flesh); row2 two COCONUT shell/flesh fragments (brown curved shell white interior), then two ORANGE wedges (orange peel, bright orange flesh); row3 two PEAR fragments (mint-green peel, cream flesh), then two PINEAPPLE fragments (yellow flesh, small ochre rind edges); row4 two STRAWBERRY fragments (red flesh with a few pale seeds), then two WATERMELON fragments (red flesh black seeds green rind). All pieces must look like 3D polygonal broken fruit chunks, match the simple low-poly game meshes in the reference, be easily readable at small size and suitable for spinning Niagara sprite particles. No stems or leaves except tiny fruit rind details. Keep every cell background transparent.
