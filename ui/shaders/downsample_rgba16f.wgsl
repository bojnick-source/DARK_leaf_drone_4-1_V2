// downsample_rgba16f.wgsl — HDR scene-color pyramid downsampler
// Generates mip levels for rgba16float scene color texture.
// Uses a 2×2 box filter (average) with Karis-average weighting
// to prevent firefly artifacts from bright HDR highlights (e.g. star
// specular) bleeding into the frosted glass blur.
//
// Part of the Glass System 100/100 render pipeline.
// Each dispatch reads mip N and writes mip N+1 at half resolution.

struct DownsampleParams {
  srcResolution : vec2<f32>,
  _pad0 : f32,
  _pad1 : f32,
};

@group(0) @binding(0) var srcTex : texture_2d<f32>;
@group(0) @binding(1) var dstTex : texture_storage_2d<rgba16float, write>;
@group(0) @binding(2) var<uniform> params : DownsampleParams;

// Karis average weight: reduces contribution of bright pixels to prevent
// firefly propagation through the mip chain.
fn karisWeight(color : vec3<f32>) -> f32 {
  let luma = dot(color, vec3<f32>(0.2126, 0.7152, 0.0722));
  return 1.0 / (1.0 + luma);
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid : vec3<u32>) {
  let dstCoord = vec2<i32>(gid.xy);
  let dstRes = vec2<i32>(params.srcResolution) / 2;

  if (dstCoord.x >= dstRes.x || dstCoord.y >= dstRes.y) {
    return;
  }

  // Source texel coordinates (2×2 block in the higher-res mip)
  let srcBase = dstCoord * 2;

  let c00 = textureLoad(srcTex, srcBase + vec2<i32>(0, 0), 0);
  let c10 = textureLoad(srcTex, srcBase + vec2<i32>(1, 0), 0);
  let c01 = textureLoad(srcTex, srcBase + vec2<i32>(0, 1), 0);
  let c11 = textureLoad(srcTex, srcBase + vec2<i32>(1, 1), 0);

  // Karis-weighted average to suppress HDR fireflies in the blur chain
  let w00 = karisWeight(c00.rgb);
  let w10 = karisWeight(c10.rgb);
  let w01 = karisWeight(c01.rgb);
  let w11 = karisWeight(c11.rgb);

  let totalWeight = w00 + w10 + w01 + w11;
  let invW = select(0.25, 1.0 / totalWeight, totalWeight > 0.0);

  let result = (c00 * w00 + c10 * w10 + c01 * w01 + c11 * w11) * invW;

  textureStore(dstTex, dstCoord, result);
}
