# Wood background

Generated using the built-in `image_gen` tool (opaque image). Source: `T_WoodBackground.png`.
The Unreal texture uses mirrored addressing in both axes so repeat boundaries
remain continuous even where generated grain at opposite image borders differs.
The imported texture is stretched to power-of-two dimensions for mipmaps and
limited to 1024px. The PNG source remains unchanged.

Ready-to-apply material instance: `/Game/Root/Assets/Materials/Backgrounds/MI_WoodBackground`.
The material now uses WorldAlignedTexture XYZ projection, independent of mesh UVs
and object scale. `TileSizeCm` defaults to 100 cm per texture tile; enlarging a cube
adds repeats instead of stretching the wood. `TilingU` and `TilingV` multiply world
density (horizontal and vertical); `Brightness` retains the instance's setting.
The background material is unlit so it keeps its color independent of scene lighting.

Exact prompt:

Use case: stylized-concept. Asset type: a seamless tileable base-color wood texture for a simple low-poly Fruit Ninja style game's background, applied directly to a cube in Unreal. Generate a square 1024x1024 flat orthographic texture of four broad VERTICAL wooden planks. Completely fill the image with the wood surface. Medium-dark warm chestnut brown, slightly desaturated so bright fruit silhouettes read clearly. Simple stylized hand-painted polygonal surfaces, a few broad low-contrast angular grain streaks running vertically, very restrained wood detail and small subtle knots. Narrow, straight, consistent dark brown grooves separating the planks. The design must tile seamlessly in BOTH directions: plank spacing is exactly periodic across left/right, wood grain continues cleanly across top/bottom, opposing border colors and grain positions match perfectly. The left and right image edges are at the centers of matching plank grooves. Uniform neutral albedo illumination, consistent brightness throughout, no lighting gradient, no highlights, no cast shadows, no vignette, no perspective, no bevel shading, no frame, no border, no text, no logos, no objects, no nails, no cracks or decorative carving. Keep it clean, simple and readable as a quiet background, not photorealistic, not a 3D mockup. Fully opaque RGB texture, no transparency. Output only the single seamless texture.
