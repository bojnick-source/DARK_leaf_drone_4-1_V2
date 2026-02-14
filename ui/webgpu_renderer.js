/* ui/webgpu_renderer.js — WebGPU CAD Render Pipeline Architecture
   Mesh3D Enhanced Mode: toggleable Clean CAD / Enhanced CAD+ viewport.

   This module provides a reference render-graph architecture for
   WebGPU-based CAD rendering.  It exposes a RenderGraph executor,
   a CADViewportRenderer with pass hooks, and dynamic-resolution /
   idle-supersample state management.

   The renderer gracefully degrades: when WebGPU is unavailable the
   exported `isWebGPUSupported()` helper returns false and the caller
   can fall back to the Three.js path in cad_viewer.js.
*/

"use strict";

// ---------------------------------------------------------------------------
// Feature detection
// ---------------------------------------------------------------------------
function isWebGPUSupported() {
  return typeof navigator !== "undefined" && !!navigator.gpu;
}

// ---------------------------------------------------------------------------
// Render-toggle state
// ---------------------------------------------------------------------------

/** @type {"CLEAN_CAD"|"ENHANCED_CAD_PLUS"} */
const DEFAULT_MODE = "CLEAN_CAD";

function createDefaultToggles() {
  return {
    mode: DEFAULT_MODE,
    taaEnabled: true,
    ssaoLevel: 1,          // 0=Off, 1=Low, 2=High
    idleSSAA: 1.0,         // 1.0 | 1.25 | 1.5 | 2.0
    hiddenLines: "OFF",    // "OFF" | "GHOST" | "HIDDEN_LINE"
    edges: {
      sharp: true,
      silhouette: true,
      curvature: false,
      screenSpace: true,
    },
    sectionPlaneEnabled: false,
    dynamicResolution: {
      enabled: true,
      minScale: 0.7,
      maxScale: 2.0,
    },
  };
}

// ---------------------------------------------------------------------------
// RenderGraph — sequential pass executor
// ---------------------------------------------------------------------------

class RenderGraph {
  constructor() {
    /** @type {Array<function(GPUCommandEncoder): void>} */
    this._passes = [];
  }

  addPass(fn) {
    this._passes.push(fn);
  }

  execute(device) {
    const encoder = device.createCommandEncoder();
    for (const pass of this._passes) {
      pass(encoder);
    }
    device.queue.submit([encoder.finish()]);
    this._passes = [];
  }
}

// ---------------------------------------------------------------------------
// CADViewportRenderer — multi-pass CAD renderer
// ---------------------------------------------------------------------------

class CADViewportRenderer {
  /**
   * @param {GPUDevice} device
   * @param {ReturnType<typeof createDefaultToggles>} toggles
   */
  constructor(device, toggles) {
    this._device = device;
    this._toggles = { ...toggles };

    // Render targets (created on first resize)
    this._rtDepth = null;
    this._rtNormals = null;
    this._rtMaterial = null;
    this._rtID = null;
    this._rtAO = null;
    this._rtColorHDR = null;
    this._rtEdges = null;
    this._rtTAAHistory = null;

    // Pipelines (initialised lazily)
    this._pipeDepth = null;
    this._pipeGBuffer = null;
    this._pipeShade = null;
    this._pipeSSAO = null;
    this._pipeEdgesScreen = null;
    this._pipeEdgesAnalytic = null;
    this._pipeComposite = null;
    this._pipeTAA = null;

    // Edge adjacency buffers (precomputed on mesh upload)
    this._edgeIndexBuffer = null;
    this._edgeMetaBuffer = null;

    // Dynamic resolution / idle-supersample state
    this._motionActive = false;
    this._lastCameraMoveMs = 0;
  }

  /** Merge partial toggle updates. */
  setToggles(next) {
    Object.assign(this._toggles, next);
  }

  /** Mark camera as having just moved (resets idle timer). */
  notifyCameraMoved(nowMs) {
    this._motionActive = true;
    this._lastCameraMoveMs = nowMs;
  }

  /** Compute the render-resolution scale factor. */
  _getRenderScale(nowMs) {
    const dr = this._toggles.dynamicResolution;
    if (!dr.enabled) {
      return 1.0;
    }

    const idleMs = nowMs - this._lastCameraMoveMs;

    if (idleMs < 120) {
      // Camera moving → reduce resolution for performance
      return Math.max(dr.minScale, 0.75);
    }
    if (idleMs < 400) {
      // Camera settling → native resolution
      return 1.0;
    }
    // Camera idle → supersample
    return this._toggles.idleSSAA;
  }

  /**
   * Build one frame worth of passes into the graph.
   * @param {number} nowMs  performance.now()
   * @param {RenderGraph} graph
   */
  render(nowMs, graph) {
    const scale = this._getRenderScale(nowMs);

    // 1) Depth Prepass
    graph.addPass((enc) => this._depthPrepass(enc, scale));

    // 2) GBuffer (normals + material IDs)
    graph.addPass((enc) => this._gbufferPass(enc, scale));

    // 3) SSAO (compute)
    if (this._toggles.ssaoLevel !== 0) {
      graph.addPass((enc) => this._ssao(enc, scale));
    }

    // 4) Shading (Studio HDRI + PBR Noir)
    graph.addPass((enc) => this._shade(enc, scale));

    // 5) Edge System
    if (this._toggles.edges.screenSpace) {
      graph.addPass((enc) => this._edgesScreenSpace(enc));
    }
    if (this._toggles.edges.sharp || this._toggles.edges.silhouette) {
      graph.addPass((enc) => this._edgesAnalytic(enc));
    }

    // 6) Selection outline (ID-buffer based)
    graph.addPass((enc) => this._selectionOutline(enc));

    // 7) TAA Resolve
    if (this._toggles.taaEnabled) {
      graph.addPass((enc) => this._taaResolve(enc));
    }

    // 8-10) Composite: tone-map + bloom + dither + UI overlay
    graph.addPass((enc) => this._composite(enc));
  }

  // -- Pass stubs (each logs intent; real GPU work requires pipeline setup) --

  _depthPrepass(enc, scale) {
    // Depth-only render to rtDepth for early-Z and stable edge input.
    void enc; void scale;
  }

  _gbufferPass(enc, scale) {
    // Write view-space normals, material IDs, object IDs into GBuffer targets.
    void enc; void scale;
  }

  _ssao(enc, scale) {
    // GTAO / SSAO compute dispatch → rtAO with optional temporal stabilisation.
    void enc; void scale;
  }

  _shade(enc, scale) {
    // Studio HDRI + PBR noir materials → rtColorHDR.
    // CLEAN_CAD: simple studio lighting.
    // ENHANCED_CAD_PLUS: curvature emphasis + MatCap option.
    void enc; void scale;
  }

  _edgesScreenSpace(enc) {
    // Compute edges from depth/normal discontinuities → rtEdges.
    // Uses edges_screen.wgsl shader.
    void enc;
  }

  _edgesAnalytic(enc) {
    // Draw line list from edgeIndexBuffer (sharp / silhouette edges).
    // Silhouette edges use view-dependent alpha in the line shader.
    void enc;
  }

  _taaResolve(enc) {
    // History reprojection + neighbourhood clamping → stable lines, no shimmer.
    void enc;
  }

  _composite(enc) {
    // Tone-map (ACES filmic), subtle highlight-only bloom, dither/noise,
    // then UI overlay composited in linear space.
    void enc;
  }

  _selectionOutline(enc) {
    // Draw selection outlines using object ID buffer.
    // Compares adjacent IDs to detect silhouette of selected object,
    // then composites a restrained glow (ink-teal accent) outline.
    void enc;
  }
}

// ---------------------------------------------------------------------------
// Async initialiser
// ---------------------------------------------------------------------------

/**
 * Request a GPUDevice and construct the renderer.
 * @returns {Promise<{device: GPUDevice, renderer: CADViewportRenderer, graph: RenderGraph}|null>}
 */
async function initWebGPURenderer() {
  if (!isWebGPUSupported()) {
    return null;
  }

  try {
    const adapter = await navigator.gpu.requestAdapter({
      powerPreference: "high-performance",
    });
    if (!adapter) {
      return null;
    }

    const device = await adapter.requestDevice({
      requiredFeatures: [],
      requiredLimits: {},
    });

    const toggles = createDefaultToggles();
    const renderer = new CADViewportRenderer(device, toggles);
    const graph = new RenderGraph();

    return { device, renderer, graph };
  } catch (_err) {
    // Silent failure: caller checks null return and falls back to Three.js
    return null;
  }
}

// ---------------------------------------------------------------------------
// Exports (browser global)
// ---------------------------------------------------------------------------

window.Mesh3DWebGPU = {
  isWebGPUSupported,
  createDefaultToggles,
  RenderGraph,
  CADViewportRenderer,
  initWebGPURenderer,
};
