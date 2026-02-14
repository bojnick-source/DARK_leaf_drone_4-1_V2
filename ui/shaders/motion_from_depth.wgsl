// motion_from_depth.wgsl — Motion vector generation from depth reprojection
// Outputs per-pixel velocity in UV space for TAA history reprojection.
// Works with reverse-Z depth buffer and standard view-projection matrices.
//
// Part of the CAD-Tuned TAA pipeline.
// Each pixel is unprojected to world space using the current frame's
// inverse view-projection, then reprojected using the previous frame's
// view-projection.  The difference in UV coordinates gives the velocity.

struct MotionParams {
  viewport     : vec2<f32>,
  nearPlane    : f32,
  farPlane     : f32,
  invCurrVP    : mat4x4<f32>,
  prevVP       : mat4x4<f32>,
};

@group(0) @binding(0) var depthTex : texture_depth_2d;
@group(0) @binding(1) var outVelocity : texture_storage_2d<rg16float, write>;
@group(0) @binding(2) var<uniform> params : MotionParams;

fn uvFromCoord(coord : vec2<i32>, res : vec2<f32>) -> vec2<f32> {
  return (vec2<f32>(coord) + 0.5) / res;
}

fn clipFromUVDepth(uv : vec2<f32>, depth : f32) -> vec4<f32> {
  // UV (0..1) → NDC (−1..+1), with Y flipped for Vulkan/WebGPU convention.
  let ndc = vec2<f32>(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0);
  return vec4<f32>(ndc, depth, 1.0);
}

fn uvFromClip(clip : vec4<f32>) -> vec2<f32> {
  let ndc = clip.xy / clip.w;
  return vec2<f32>(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5);
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid : vec3<u32>) {
  let coord = vec2<i32>(gid.xy);
  let res = params.viewport;

  if (f32(coord.x) >= res.x || f32(coord.y) >= res.y) {
    return;
  }

  // Read reverse-Z depth for this pixel
  let depth = textureLoad(depthTex, coord, 0);

  // Current UV position
  let currUV = uvFromCoord(coord, res);

  // Unproject to world space using inverse current view-projection
  let clipCurr = clipFromUVDepth(currUV, depth);
  let worldH   = params.invCurrVP * clipCurr;
  let worldPos = worldH.xyz / worldH.w;

  // Reproject into previous frame using previous view-projection
  let clipPrev = params.prevVP * vec4<f32>(worldPos, 1.0);
  let prevUV   = uvFromClip(clipPrev);

  // Velocity = current − previous (in UV space)
  let velocity = currUV - prevUV;

  textureStore(outVelocity, coord, vec4<f32>(velocity, 0.0, 1.0));
}
