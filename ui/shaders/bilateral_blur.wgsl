// bilateral_blur.wgsl — Depth-aware cross-bilateral blur
// Applies a Gaussian-weighted blur to the HDR color pyramid, using the
// linear depth pyramid to reject samples that cross depth discontinuities.
// This prevents star/geometry "bleeding" across glass panel edges — the
// critical difference between toy blur and ship-grade frosted glass.
//
// Part of the Glass System 100/100 render pipeline.
// Runs per-mip on the HDR color pyramid after downsample.

struct BlurParams {
  resolution : vec2<f32>,
  direction : vec2<f32>,   // (1,0) for horizontal, (0,1) for vertical
  depthSigma : f32,        // depth rejection threshold (view-space units)
  spatialSigma : f32,      // spatial Gaussian sigma (pixels)
  kernelRadius : i32,      // half-width of the blur kernel
  _pad0 : i32,
};

@group(0) @binding(0) var colorTex : texture_2d<f32>;
@group(0) @binding(1) var depthTex : texture_2d<f32>;
@group(0) @binding(2) var outColor : texture_storage_2d<rgba16float, write>;
@group(0) @binding(3) var<uniform> params : BlurParams;

fn gaussianWeight(offset : f32, sigma : f32) -> f32 {
  return exp(-0.5 * (offset * offset) / (sigma * sigma));
}

fn depthWeight(centerDepth : f32, sampleDepth : f32, sigma : f32) -> f32 {
  let diff = abs(centerDepth - sampleDepth);
  return exp(-0.5 * (diff * diff) / (sigma * sigma));
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid : vec3<u32>) {
  let coord = vec2<i32>(gid.xy);
  let res = vec2<i32>(params.resolution);

  if (coord.x >= res.x || coord.y >= res.y) {
    return;
  }

  let centerColor = textureLoad(colorTex, coord, 0);
  let centerDepth = textureLoad(depthTex, coord, 0).r;

  var accumColor = vec4<f32>(0.0);
  var accumWeight = 0.0;

  let dir = vec2<i32>(params.direction);

  for (var i = -params.kernelRadius; i <= params.kernelRadius; i = i + 1) {
    let sampleCoord = coord + dir * i;

    // Clamp to texture bounds
    let clamped = clamp(sampleCoord, vec2<i32>(0, 0), res - vec2<i32>(1, 1));

    let sampleColor = textureLoad(colorTex, clamped, 0);
    let sampleDepth = textureLoad(depthTex, clamped, 0).r;

    // Spatial Gaussian weight
    let gw = gaussianWeight(f32(i), params.spatialSigma);

    // Depth-aware bilateral weight — rejects samples across depth edges
    let dw = depthWeight(centerDepth, sampleDepth, params.depthSigma);

    let w = gw * dw;
    accumColor = accumColor + sampleColor * w;
    accumWeight = accumWeight + w;
  }

  // Normalize; fall back to center pixel if no valid neighbors
  let invWeight = select(1.0, 1.0 / accumWeight, accumWeight > 0.001);
  let result = select(centerColor, accumColor * invWeight, accumWeight > 0.001);

  textureStore(outColor, coord, result);
}
