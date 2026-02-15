// taa_resolve.wgsl — CAD-Tuned Temporal Anti-Aliasing Resolve
// Production-grade, edge-safe, Shapr3D/Autodesk-style stability.
//
// Features:
//   1. Motion-vector reprojection from history buffer
//   2. Neighborhood clamp (AABB / variance) to prevent ghosting
//   3. Depth rejection for disoccluded pixels
//   4. CAD edge/reactive mask to protect sharp edges + UI overlays
//   5. Responsive sharpening to avoid "TAA mush" on thin lines
//
// Inputs:
//   - currentColor : rgba16float — current frame HDR scene color
//   - historyColor : rgba16float — previous TAA output (to reproject)
//   - velocityTex  : rg16float — per-pixel UV-space motion vectors
//   - depthTex     : depth texture for depth-rejection
//   - reactiveMask : r8unorm — CAD edge / UI reactive mask (1 = protect)
//
// Output:
//   - outColor : rgba16float — resolved TAA result (becomes next history)

struct TAAParams {
  resolution       : vec2<f32>,
  blendMin         : f32,   // minimum history weight (e.g. 0.05 → responsive)
  blendMax         : f32,   // maximum history weight (e.g. 0.12 → stable)
  depthRejection   : f32,   // depth threshold for disocclusion detection
  reactiveBoost    : f32,   // how much reactive pixels reduce history weight
  sharpenStrength  : f32,   // CAS-like sharpening for CAD crispness
  _pad0            : f32,
};

@group(0) @binding(0) var currentColor : texture_2d<f32>;
@group(0) @binding(1) var historyColor : texture_2d<f32>;
@group(0) @binding(2) var velocityTex  : texture_2d<f32>;
@group(0) @binding(3) var depthTex     : texture_depth_2d;
@group(0) @binding(4) var reactiveMask : texture_2d<f32>;
@group(0) @binding(5) var outColor     : texture_storage_2d<rgba16float, write>;
@group(0) @binding(6) var<uniform> params : TAAParams;

// ---- Color-space helpers ----

fn rgbToYCoCg(rgb : vec3<f32>) -> vec3<f32> {
  // Luma-chroma space for tighter neighborhood clamping.
  let y  = dot(rgb, vec3<f32>(0.25, 0.5, 0.25));
  let co = dot(rgb, vec3<f32>(0.5, 0.0, -0.5));
  let cg = dot(rgb, vec3<f32>(-0.25, 0.5, -0.25));
  return vec3<f32>(y, co, cg);
}

fn yCoCgToRgb(ycocg : vec3<f32>) -> vec3<f32> {
  let y  = ycocg.x;
  let co = ycocg.y;
  let cg = ycocg.z;
  return vec3<f32>(y + co - cg, y + cg, y - co - cg);
}

// ---- Neighborhood clamp (variance-based AABB in YCoCg) ----

fn neighborhoodClamp(
  center : vec3<f32>,
  history : vec3<f32>,
  coord : vec2<i32>,
  res : vec2<i32>
) -> vec3<f32> {
  // Gather 3×3 neighborhood in YCoCg space for min/max AABB.
  var aabbMin = vec3<f32>(1e10);
  var aabbMax = vec3<f32>(-1e10);
  var moment1 = vec3<f32>(0.0);
  var moment2 = vec3<f32>(0.0);

  for (var dy = -1; dy <= 1; dy = dy + 1) {
    for (var dx = -1; dx <= 1; dx = dx + 1) {
      let sc = clamp(coord + vec2<i32>(dx, dy),
                      vec2<i32>(0, 0),
                      res - vec2<i32>(1, 1));
      let sampleRGB = textureLoad(currentColor, sc, 0).rgb;
      let sampleYCoCg = rgbToYCoCg(sampleRGB);
      aabbMin = min(aabbMin, sampleYCoCg);
      aabbMax = max(aabbMax, sampleYCoCg);
      moment1 = moment1 + sampleYCoCg;
      moment2 = moment2 + sampleYCoCg * sampleYCoCg;
    }
  }

  // Variance-based tightening: shrink AABB towards mean ± 1σ
  let mean = moment1 / 9.0;
  let variance = moment2 / 9.0 - mean * mean;
  let sigma = sqrt(max(variance, vec3<f32>(0.0)));
  let varMin = mean - sigma;
  let varMax = mean + sigma;

  // Use tighter of AABB and variance bounds
  let clampMin = max(aabbMin, varMin);
  let clampMax = min(aabbMax, varMax);

  return clamp(history, clampMin, clampMax);
}

// ---- Depth rejection ----

fn linearizeDepth(d : f32) -> f32 {
  // Linearize reverse-Z depth.
  let near = 0.01;
  let far = 100.0;
  return near * far / (far - d * (far - near));
}

fn depthRejectionFactor(
  coord : vec2<i32>,
  histCoord : vec2<i32>,
  res : vec2<i32>,
  threshold : f32
) -> f32 {
  let currDepthRaw = textureLoad(depthTex, coord, 0);
  let histClamped = clamp(histCoord, vec2<i32>(0, 0), res - vec2<i32>(1, 1));
  let histDepthRaw = textureLoad(depthTex, histClamped, 0);

  let currLinear = linearizeDepth(currDepthRaw);
  let histLinear = linearizeDepth(histDepthRaw);

  let diff = abs(currLinear - histLinear) / max(currLinear, 0.001);
  return saturate(1.0 - diff / threshold);
}

// ---- CAS-like responsive sharpening ----

fn sharpen(coord : vec2<i32>, center : vec3<f32>, res : vec2<i32>, strength : f32) -> vec3<f32> {
  // Simple cross-shaped unsharp mask for CAD edge crispness.
  let l = textureLoad(currentColor, clamp(coord + vec2<i32>(-1, 0), vec2<i32>(0), res - vec2<i32>(1)), 0).rgb;
  let r = textureLoad(currentColor, clamp(coord + vec2<i32>( 1, 0), vec2<i32>(0), res - vec2<i32>(1)), 0).rgb;
  let u = textureLoad(currentColor, clamp(coord + vec2<i32>( 0,-1), vec2<i32>(0), res - vec2<i32>(1)), 0).rgb;
  let d = textureLoad(currentColor, clamp(coord + vec2<i32>( 0, 1), vec2<i32>(0), res - vec2<i32>(1)), 0).rgb;

  let neighbors = (l + r + u + d) * 0.25;
  let sharpened = center + (center - neighbors) * strength;
  return max(sharpened, vec3<f32>(0.0));
}

// ---- Main TAA Resolve ----

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid : vec3<u32>) {
  let coord = vec2<i32>(gid.xy);
  let res = vec2<i32>(params.resolution);

  if (coord.x >= res.x || coord.y >= res.y) {
    return;
  }

  // --- Sample current frame ---
  let currentRGB = textureLoad(currentColor, coord, 0).rgb;

  // --- Read motion vector and compute history sample position ---
  let velocity = textureLoad(velocityTex, coord, 0).rg;
  let currUV = (vec2<f32>(coord) + 0.5) / vec2<f32>(res);
  let histUV = currUV - velocity;
  let histCoord = vec2<i32>(histUV * vec2<f32>(res));

  // --- Check if history is within bounds ---
  let inBounds = histCoord.x >= 0 && histCoord.x < res.x &&
                 histCoord.y >= 0 && histCoord.y < res.y;

  // --- Sample history (clamp to border for safety) ---
  let histClamped = clamp(histCoord, vec2<i32>(0, 0), res - vec2<i32>(1, 1));
  var historyRGB = textureLoad(historyColor, histClamped, 0).rgb;

  // --- Neighborhood clamp in YCoCg to prevent ghosting ---
  let historyYCoCg = rgbToYCoCg(historyRGB);
  let clampedYCoCg = neighborhoodClamp(
    rgbToYCoCg(currentRGB), historyYCoCg, coord, res
  );
  historyRGB = yCoCgToRgb(clampedYCoCg);

  // --- Depth rejection: reduce history trust for disoccluded pixels ---
  let depthTrust = depthRejectionFactor(coord, histCoord, res, params.depthRejection);

  // --- Reactive mask: CAD edges / UI get higher responsiveness ---
  let reactive = textureLoad(reactiveMask, coord, 0).r;
  let reactiveWeight = reactive * params.reactiveBoost;

  // --- Compute adaptive blend factor ---
  // Base factor modulated by depth trust, reactive mask, and bounds check
  var blendFactor = params.blendMin;
  if (inBounds) {
    // More history when trusted; less when disoccluded or reactive
    blendFactor = mix(params.blendMin, params.blendMax, depthTrust);
    blendFactor = max(blendFactor - reactiveWeight, params.blendMin);
  }

  // When velocity is high (camera moving fast), lean more towards current frame
  let speed = length(velocity) * max(params.resolution.x, params.resolution.y);
  let motionReduction = saturate(speed * 0.5);
  blendFactor = mix(blendFactor, params.blendMin, motionReduction);

  // --- Blend current frame with clamped history ---
  var resolved = mix(currentRGB, historyRGB, 1.0 - blendFactor);

  // --- Apply CAS-like sharpening to preserve CAD edge crispness ---
  if (params.sharpenStrength > 0.0) {
    resolved = sharpen(coord, resolved, res, params.sharpenStrength);
  }

  textureStore(outColor, coord, vec4<f32>(resolved, 1.0));
}
