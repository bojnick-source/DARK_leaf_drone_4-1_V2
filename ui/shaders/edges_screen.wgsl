// edges_screen.wgsl — Screen-space edge detection (depth + normal discontinuities)
// Produces stable CAD-like edges from normal/depth discontinuities (robust fallback).
// Combine with analytic edges for "real CAD feel".
//
// Part of the Mesh3D Enhanced Mode render pipeline.
// Intended for WebGPU compute pass; reads depth and normal GBuffer textures
// and writes a single-channel edge intensity to a storage texture.

struct Params {
  resolution : vec2<f32>,
  depthThreshold : f32,
  normalThreshold : f32,
  edgeWidth : f32,
  _pad0 : f32,
  _pad1 : f32,
  _pad2 : f32,
};

@group(0) @binding(0) var depthTex : texture_depth_2d;
@group(0) @binding(1) var normalTex : texture_2d<f32>;
@group(0) @binding(2) var outEdges : texture_storage_2d<r8unorm, write>;
@group(0) @binding(3) var<uniform> params : Params;

fn sampleDepth(coord : vec2<i32>) -> f32 {
  let clamped = clamp(coord,
    vec2<i32>(0, 0),
    vec2<i32>(params.resolution) - vec2<i32>(1, 1));
  return textureLoad(depthTex, clamped, 0);
}

fn sampleNormal(coord : vec2<i32>) -> vec3<f32> {
  let clamped = clamp(coord,
    vec2<i32>(0, 0),
    vec2<i32>(params.resolution) - vec2<i32>(1, 1));
  return textureLoad(normalTex, clamped, 0).xyz * 2.0 - 1.0;
}

fn linearizeDepth(d : f32) -> f32 {
  // Linearize reverse-Z depth for stable comparison.
  // Near=0.01, Far=100.0 assumed; override via uniform if needed.
  let near = 0.01;
  let far = 100.0;
  return near * far / (far - d * (far - near));
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid : vec3<u32>) {
  let coord = vec2<i32>(gid.xy);
  let res = vec2<i32>(params.resolution);

  if (coord.x >= res.x || coord.y >= res.y) {
    return;
  }

  // --- Depth-based edge detection (Roberts cross operator) ---
  let d00 = linearizeDepth(sampleDepth(coord + vec2<i32>(0, 0)));
  let d10 = linearizeDepth(sampleDepth(coord + vec2<i32>(1, 0)));
  let d01 = linearizeDepth(sampleDepth(coord + vec2<i32>(0, 1)));
  let d11 = linearizeDepth(sampleDepth(coord + vec2<i32>(1, 1)));

  let depthEdge = abs(d00 - d11) + abs(d10 - d01);
  let depthFactor = smoothstep(
    params.depthThreshold * 0.5,
    params.depthThreshold,
    depthEdge);

  // --- Normal-based edge detection (Sobel-like) ---
  let n_c  = sampleNormal(coord);
  let n_l  = sampleNormal(coord + vec2<i32>(-1, 0));
  let n_r  = sampleNormal(coord + vec2<i32>( 1, 0));
  let n_u  = sampleNormal(coord + vec2<i32>( 0,-1));
  let n_d  = sampleNormal(coord + vec2<i32>( 0, 1));

  let normalDiffH = 1.0 - dot(n_l, n_r);
  let normalDiffV = 1.0 - dot(n_u, n_d);
  let normalEdge  = max(normalDiffH, normalDiffV);
  let normalFactor = smoothstep(
    params.normalThreshold * 0.5,
    params.normalThreshold,
    normalEdge);

  // --- Combine: max of depth and normal edges ---
  let edge = max(depthFactor, normalFactor);

  // --- Optional edge width expansion via dilation-like kernel ---
  var dilated = edge;
  if (params.edgeWidth > 1.0) {
    let radius = i32(params.edgeWidth);
    for (var dy = -radius; dy <= radius; dy = dy + 1) {
      for (var dx = -radius; dx <= radius; dx = dx + 1) {
        let sc = coord + vec2<i32>(dx, dy);
        if (sc.x >= 0 && sc.x < res.x && sc.y >= 0 && sc.y < res.y) {
          let sd = linearizeDepth(sampleDepth(sc));
          let sn = sampleNormal(sc);
          let sDe = abs(sd - d00);
          let sNe = 1.0 - dot(sn, n_c);
          let sE = max(
            smoothstep(params.depthThreshold * 0.5, params.depthThreshold, sDe),
            smoothstep(params.normalThreshold * 0.5, params.normalThreshold, sNe));
          dilated = max(dilated, sE * 0.6);
        }
      }
    }
  }

  textureStore(outEdges, coord, vec4<f32>(dilated, 0.0, 0.0, 1.0));
}
