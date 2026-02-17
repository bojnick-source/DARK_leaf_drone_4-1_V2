// glass_composite.wgsl — Beer–Lambert absorption + Weighted Blended OIT
// Final compositing pass for the Glass System 100/100 pipeline.
//
// Combines:
//   1) Beer–Lambert absorption: attenuates background light through noir
//      glass with physically-based exponential falloff by thickness.
//      Enhanced with depth-dependent thickness, chromatic dispersion,
//      and minimum transmittance floor.
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
  chromaticDispersion : f32,    // chromatic dispersion strength (0 = off)
  minTransmittance : f32,       // energy floor to prevent over-darkening
  depthScale : f32,             // depth-to-thickness scale factor
  _pad0 : f32,
};

@group(0) @binding(0) var blurredScene : texture_2d<f32>;
@group(0) @binding(1) var oitAccum : texture_2d<f32>;
@group(0) @binding(2) var oitReveal : texture_2d<f32>;
@group(0) @binding(3) var linearDepth : texture_2d<f32>;
@group(0) @binding(4) var outColor : texture_storage_2d<rgba16float, write>;
@group(0) @binding(5) var<uniform> params : GlassParams;

// Beer–Lambert transmittance: T = exp(-σ · d · color)
// Models light absorption through a tinted medium of given thickness.
fn beerLambert(absorptionCoeff : vec3<f32>, density : f32, dist : f32) -> vec3<f32> {
  return exp(-absorptionCoeff * density * dist);
}

// Chromatic dispersion: shorter wavelengths (blue) are absorbed faster
// than longer wavelengths (red) in real glass. Apply a per-channel
// exponent shift proportional to the dispersion strength.
fn chromaticAbsorption(
  absorptionCoeff : vec3<f32>,
  density : f32,
  dist : f32,
  dispersion : f32
) -> vec3<f32> {
  // Per-channel dispersion multipliers: R < G < B extinction
  let channelScale = vec3<f32>(
    1.0 - dispersion * 0.15,   // red — least absorption
    1.0,                       // green — reference
    1.0 + dispersion * 0.25    // blue — most absorption
  );
  return exp(-absorptionCoeff * channelScale * density * dist);
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
  let depth = textureLoad(linearDepth, coord, 0).r;

  // --- Weighted Blended OIT resolve ---
  // McGuire & Bavoil 2013: Ci/ai for premultiplied glass color
  let oitColor = select(
    vec3<f32>(0.0),
    accum.rgb / max(accum.a, 0.00001),
    accum.a > 0.00001
  );

  // --- Depth-dependent thickness ---
  // Modulate base thickness by the per-pixel linear depth so that
  // absorption varies with distance — thicker apparent glass at
  // grazing angles or deeper geometry.
  let depthFactor = 1.0 + depth * params.depthScale;
  let effectiveThickness = params.thickness * depthFactor;

  // --- Beer–Lambert absorption through noir glass ---
  // Use chromatic dispersion when enabled for wavelength-dependent
  // extinction; otherwise fall back to the classic uniform model.
  var transmittance : vec3<f32>;
  if (params.chromaticDispersion > 0.0) {
    transmittance = chromaticAbsorption(
      params.absorptionColor,
      params.absorptionDensity,
      effectiveThickness,
      params.chromaticDispersion
    );
  } else {
    transmittance = beerLambert(
      params.absorptionColor,
      params.absorptionDensity,
      effectiveThickness
    );
  }

  // Clamp to minimum transmittance floor to prevent over-darkening
  transmittance = max(transmittance, vec3<f32>(params.minTransmittance));

  // Apply absorption to background (the blurred scene behind the glass)
  let absorbedBg = background.rgb * transmittance;

  // --- Composite: OIT glass over absorbed background ---
  // revealage = 1.0 → fully transparent (no glass), 0.0 → fully opaque glass
  let composited = oitColor * (1.0 - revealage) + absorbedBg * revealage;

  // --- Subtle Fresnel-like rim (compute-safe screen-space approximation) ---
  // Use local revealage differences as a proxy for an edge metric.
  let leftCoord = vec2<i32>(max(coord.x - 1, 0), coord.y);
  let rightCoord = vec2<i32>(min(coord.x + 1, res.x - 1), coord.y);
  let upCoord = vec2<i32>(coord.x, max(coord.y - 1, 0));
  let downCoord = vec2<i32>(coord.x, min(coord.y + 1, res.y - 1));

  let revealL = textureLoad(oitReveal, leftCoord, 0).r;
  let revealR = textureLoad(oitReveal, rightCoord, 0).r;
  let revealU = textureLoad(oitReveal, upCoord, 0).r;
  let revealD = textureLoad(oitReveal, downCoord, 0).r;

  let edgeGrad = abs(revealR - revealL) + abs(revealD - revealU);
  let fresnelRim = pow(saturate(edgeGrad * 2.0), params.fresnelPower) * params.fresnelIntensity;

  let finalColor = composited + vec3<f32>(fresnelRim);

  textureStore(outColor, coord, vec4<f32>(finalColor, 1.0));
}
