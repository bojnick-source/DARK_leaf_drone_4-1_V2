// glass_composite.wgsl — Beer–Lambert absorption + Weighted Blended OIT
// Final compositing pass for the Glass System 100/100 pipeline.
//
// Combines:
//   1) Beer–Lambert absorption: attenuates background light through noir
//      glass with physically-based exponential falloff by thickness.
//   2) Weighted Blended OIT (McGuire & Bavoil 2013): correct alpha
//      compositing of overlapping glass panels without sorting.
//   3) Fresnel-approximate rim specular for glass sheen.
//
// Inputs:
//   - blurredScene: depth-aware blurred HDR color from bilateral blur mips
//   - oitAccum: weighted-blended OIT accumulation (rgba16float)
//   - oitReveal: OIT revealage (r8unorm)
//   - linearDepth: scene linear depth (r32float)
//
// Part of the Glass System 100/100 render pipeline.

struct GlassParams {
  resolution : vec2<f32>,
  absorptionColor : vec3<f32>,  // noir tint RGB (log-space extinction)
  absorptionDensity : f32,      // Beer–Lambert density multiplier
  thickness : f32,              // glass panel thickness (world units)
  fresnelPower : f32,           // Fresnel rim exponent (typically 3–5)
  fresnelIntensity : f32,       // Fresnel specular brightness
  _pad0 : f32,
};

@group(0) @binding(0) var blurredScene : texture_2d<f32>;
@group(0) @binding(1) var oitAccum : texture_2d<f32>;
@group(0) @binding(2) var oitReveal : texture_2d<f32>;
@group(0) @binding(3) var outColor : texture_storage_2d<rgba16float, write>;
@group(0) @binding(4) var<uniform> params : GlassParams;

// Beer–Lambert transmittance: T = exp(-σ · d · color)
// Models light absorption through a tinted medium of given thickness.
fn beerLambert(absorptionCoeff : vec3<f32>, density : f32, dist : f32) -> vec3<f32> {
  return exp(-absorptionCoeff * density * dist);
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid : vec3<u32>) {
  let coord = vec2<i32>(gid.xy);
  let res = vec2<i32>(params.resolution);

  if (coord.x >= res.x || coord.y >= res.y) {
    return;
  }

  // --- Sample inputs ---
  let background = textureLoad(blurredScene, coord, 0);
  let accum = textureLoad(oitAccum, coord, 0);
  let revealage = textureLoad(oitReveal, coord, 0).r;

  // --- Weighted Blended OIT resolve ---
  // McGuire & Bavoil 2013: Ci/ai for premultiplied glass color
  let oitColor = select(
    vec3<f32>(0.0),
    accum.rgb / max(accum.a, 0.00001),
    accum.a > 0.00001
  );

  // --- Beer–Lambert absorption through noir glass ---
  let transmittance = beerLambert(
    params.absorptionColor,
    params.absorptionDensity,
    params.thickness
  );

  // Apply absorption to background (the blurred scene behind the glass)
  let absorbedBg = background.rgb * transmittance;

  // --- Composite: OIT glass over absorbed background ---
  // revealage = 1.0 → fully transparent (no glass), 0.0 → fully opaque glass
  let composited = oitColor * (1.0 - revealage) + absorbedBg * revealage;

  // --- Subtle Fresnel-like rim (screen-space approximation) ---
  // Uses edge luminance gradient as a proxy for surface angle.
  // Full implementation would use view-space normals; this is a fast approx.
  let luma = dot(composited, vec3<f32>(0.2126, 0.7152, 0.0722));
  let edgeGrad = fwidth(luma);
  let fresnelRim = pow(saturate(edgeGrad * 8.0), params.fresnelPower) * params.fresnelIntensity;

  let finalColor = composited + vec3<f32>(fresnelRim);

  textureStore(outColor, coord, vec4<f32>(finalColor, 1.0));
}
