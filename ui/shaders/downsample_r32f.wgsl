// downsample_r32f.wgsl — Linear depth pyramid downsampler
// Generates mip levels for r32float linear-depth texture.
// Uses min-of-4 (conservative depth) to prevent halos at silhouettes
// when the glass blur samples behind occluding geometry.
//
// Part of the Glass System 100/100 render pipeline.
// Each dispatch reads mip N and writes mip N+1 at half resolution.

struct DownsampleParams {
  srcResolution : vec2<f32>,
  _pad0 : f32,
  _pad1 : f32,
};

@group(0) @binding(0) var srcTex : texture_2d<f32>;
@group(0) @binding(1) var dstTex : texture_storage_2d<r32float, write>;
@group(0) @binding(2) var<uniform> params : DownsampleParams;

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid : vec3<u32>) {
  let dstCoord = vec2<i32>(gid.xy);
  let dstRes = vec2<i32>(params.srcResolution) / 2;

  if (dstCoord.x >= dstRes.x || dstCoord.y >= dstRes.y) {
    return;
  }

  // Source texel coordinates (2×2 block in the higher-res mip)
  let srcBase = dstCoord * 2;

  let d00 = textureLoad(srcTex, srcBase + vec2<i32>(0, 0), 0).r;
  let d10 = textureLoad(srcTex, srcBase + vec2<i32>(1, 0), 0).r;
  let d01 = textureLoad(srcTex, srcBase + vec2<i32>(0, 1), 0).r;
  let d11 = textureLoad(srcTex, srcBase + vec2<i32>(1, 1), 0).r;

  // Conservative (min) depth preserves closest geometry boundary.
  // This prevents blur from leaking background behind foreground edges.
  let minDepth = min(min(d00, d10), min(d01, d11));

  textureStore(dstTex, dstCoord, vec4<f32>(minDepth, 0.0, 0.0, 1.0));
}
