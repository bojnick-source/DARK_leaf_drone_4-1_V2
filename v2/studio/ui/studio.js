/**
 * @fileoverview V2 Studio — Enterprise-grade computational rendering dashboard
 * Integrates REIDCE v2 AI, Pico-GK+ topology, Monte-Carlo sampling, and engineering canvas renderers
 * with comprehensive error handling, validation, logging, and state management.
 * @version 2.0.0
 */

(function() {
  'use strict';

  // ============================================================================
  // CONFIGURATION
  // ============================================================================

  /**
   * @typedef {Object} StudioConfig
   * @property {number} fetchTimeout - Timeout for fetch requests in milliseconds
   * @property {number} clockUpdateInterval - Clock update interval in milliseconds
   * @property {string} sampleDataPath - Path to sample AI output JSON
   * @property {boolean} enableLogging - Enable console logging
   * @property {string} logLevel - Logging level (debug, info, warn, error)
   */
  const CONFIG = {
    fetchTimeout: 5000,
    clockUpdateInterval: 1000,
    sampleDataPath: './sample_ai_output.json',
    enableLogging: true,
    logLevel: 'info', // debug, info, warn, error
  };

  // ============================================================================
  // LOGGER
  // ============================================================================

  const Logger = {
    /**
     * @private
     * @type {Object.<string, number>}
     */
    _levels: {
      debug: 0,
      info: 1,
      warn: 2,
      error: 3,
    },

    /**
     * Get current log level threshold
     * @private
     * @returns {number}
     */
    _getCurrentLevel: function() {
      return this._levels[CONFIG.logLevel] || this._levels.info;
    },

    /**
     * @param {string} level
     * @param {string} message
     * @param {any} [data]
     */
    _log: function(level, message, data) {
      if (!CONFIG.enableLogging) return;
      if (this._levels[level] < this._getCurrentLevel()) return;

      const timestamp = new Date().toISOString();
      const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
      
      if (data !== undefined) {
        console[level === 'debug' ? 'log' : level](`${prefix} ${message}`, data);
      } else {
        console[level === 'debug' ? 'log' : level](`${prefix} ${message}`);
      }
    },

    debug: function(msg, data) { this._log('debug', msg, data); },
    info: function(msg, data) { this._log('info', msg, data); },
    warn: function(msg, data) { this._log('warn', msg, data); },
    error: function(msg, data) { this._log('error', msg, data); },
  };

  // ============================================================================
  // VALIDATOR
  // ============================================================================

  const Validator = {
    /**
     * Validate that a value is a non-negative number
     * @private
     * @param {*} value
     * @param {string} fieldName
     * @param {Array<string>} errors
     */
    _validateNonNegativeNumber: function(value, fieldName, errors) {
      if (value !== undefined && (typeof value !== 'number' || value < 0)) {
        errors.push(`${fieldName} must be a non-negative number`);
      }
    },

    /**
     * Validate that a value is a number in a specific range
     * @private
     * @param {*} value
     * @param {string} fieldName
     * @param {number} min
     * @param {number} max
     * @param {Array<string>} errors
     */
    _validateNumberInRange: function(value, fieldName, min, max, errors) {
      if (value !== undefined && (typeof value !== 'number' || value < min || value > max)) {
        errors.push(`${fieldName} must be a number between ${min} and ${max}`);
      }
    },

    /**
     * Validate payload structure
     * @param {Object} payload
     * @returns {{valid: boolean, errors: string[]}}
     */
    validatePayload: function(payload) {
      const errors = [];

      if (!payload || typeof payload !== 'object') {
        errors.push('Payload must be an object');
        return { valid: false, errors };
      }

      // Validate schema version if present
      if (payload.schema && typeof payload.schema !== 'string') {
        errors.push('Schema must be a string');
      }

      // Validate AI section
      if (payload.ai) {
        if (typeof payload.ai !== 'object') {
          errors.push('AI section must be an object');
        } else {
          this._validateNumberInRange(payload.ai.confidence, 'AI confidence', 0, 1, errors);
        }
      }

      // Validate CAD section
      if (payload.cad) {
        if (typeof payload.cad !== 'object') {
          errors.push('CAD section must be an object');
        } else {
          this._validateNonNegativeNumber(payload.cad.triangle_count, 'CAD triangle_count', errors);
          this._validateNumberInRange(payload.cad.mesh_score, 'CAD mesh_score', 0, 1, errors);
          if (payload.cad.wireframe !== undefined && !Array.isArray(payload.cad.wireframe)) {
            errors.push('CAD wireframe must be an array');
          }
        }
      }

      // Validate FEA section
      if (payload.fea) {
        if (typeof payload.fea !== 'object') {
          errors.push('FEA section must be an object');
        } else {
          this._validateNonNegativeNumber(payload.fea.safety_factor, 'FEA safety_factor', errors);
        }
      }

      return {
        valid: errors.length === 0,
        errors,
      };
    },

    /**
     * Sanitize number value with range check
     * @param {*} value
     * @param {number} defaultValue
     * @param {number} [min]
     * @param {number} [max]
     * @returns {number}
     */
    sanitizeNumber: function(value, defaultValue, min, max) {
      const num = typeof value === 'number' ? value : defaultValue;
      if (min !== undefined && num < min) return min;
      if (max !== undefined && num > max) return max;
      return num;
    },

    /**
     * Sanitize string value
     * @param {*} value
     * @param {string} defaultValue
     * @returns {string}
     */
    sanitizeString: function(value, defaultValue) {
      return typeof value === 'string' ? value : defaultValue;
    },
  };

  // ============================================================================
  // DOM MANAGER
  // ============================================================================

  const DOMManager = {
    /**
     * @private
     * @type {Object.<string, HTMLElement|null>}
     */
    _elements: {},

    /**
     * Initialize DOM element references
     */
    init: function() {
      const ids = [
        'statusBadge', 'btnLoadSample', 'btnExport', 'railCount', 'photonicLinks',
        'thermalNodes', 'aiBest', 'aiScore', 'aiModel', 'aiConfidence', 'aiStatus',
        'processorLabel', 'busVoltage', 'thermalMargin', 'aiRecommendation',
        'electroThermal', 'flightAlt', 'flightSpeed', 'flightMode', 'shipEfficiency',
        'kitePower', 'grossMargin', 'shippingCost', 'clock', 'flightCanvas',
        'thermalCanvas', 'windCanvas', 'salesCanvas', 'cadCanvas', 'feaCanvas',
        'feaDispCanvas', 'barAI', 'barFlight', 'barThermal', 'barWind', 'barMesh',
        'barFEA', 'valAI', 'valFlight', 'valThermal', 'valWind', 'valMesh', 'valFEA',
        'cadQuality', 'cadTriangles', 'cadVertices', 'cadMeshScore', 'cadSurfaceArea',
        'feaMaxDisp', 'feaMaxStress', 'feaSafetyFactor', 'feaConverged',
      ];

      ids.forEach(id => {
        this._elements[id] = document.getElementById(id);
        if (!this._elements[id]) {
          Logger.warn(`Element with id '${id}' not found`);
        }
      });

      Logger.info('DOM Manager initialized', { elementCount: Object.keys(this._elements).length });
    },

    /**
     * Get element by key
     * @param {string} key
     * @returns {HTMLElement|null}
     */
    get: function(key) {
      return this._elements[key] || null;
    },

    /**
     * Safely set text content
     * @param {string} key
     * @param {string} text
     */
    setText: function(key, text) {
      const el = this.get(key);
      if (el) {
        el.textContent = String(text);
      }
    },

    /**
     * Safely set attribute
     * @param {string} key
     * @param {string} attr
     * @param {string} value
     */
    setAttr: function(key, attr, value) {
      const el = this.get(key);
      if (el) {
        el.setAttribute(attr, value);
      }
    },
  };

  // ============================================================================
  // STATE MANAGER
  // ============================================================================

  const StateManager = {
    /**
     * @private
     * @type {Object|null}
     */
    _currentPayload: null,

    /**
     * @private
     * @type {Array<function(Object):void>}
     */
    _subscribers: [],

    /**
     * Get current payload
     * @returns {Object|null}
     */
    getPayload: function() {
      return this._currentPayload;
    },

    /**
     * Set new payload and notify subscribers
     * @param {Object} payload
     */
    setPayload: function(payload) {
      this._currentPayload = payload;
      Logger.debug('State updated', { payload });
      this._notifySubscribers(payload);
    },

    /**
     * Subscribe to state changes
     * @param {function(Object):void} callback
     */
    subscribe: function(callback) {
      this._subscribers.push(callback);
    },

    /**
     * @private
     */
    _notifySubscribers: function(payload) {
      this._subscribers.forEach(fn => {
        try {
          fn(payload);
        } catch (err) {
          Logger.error('Subscriber error', err);
        }
      });
    },
  };

  // ============================================================================
  // DATA LOADER
  // ============================================================================

  const DataLoader = {
    /**
     * Load sample data from JSON file
     * @returns {Promise<Object>}
     */
    loadSample: function() {
      Logger.info('Loading sample data', { path: CONFIG.sampleDataPath });
      
      return this._fetchWithTimeout(CONFIG.sampleDataPath, CONFIG.fetchTimeout)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
          return response.json();
        })
        .then(payload => {
          Logger.info('Sample data loaded successfully');
          return payload;
        })
        .catch(err => {
          Logger.warn('Failed to load sample data, using embedded fallback', err);
          return this._getEmbeddedSample();
        });
    },

    /**
     * Fetch with timeout
     * @private
     * @param {string} url
     * @param {number} timeout
     * @returns {Promise<Response>}
     */
    _fetchWithTimeout: function(url, timeout) {
      return Promise.race([
        fetch(url),
        new Promise((_, reject) => {
          setTimeout(() => reject(new Error('Fetch timeout')), timeout);
        }),
      ]);
    },

    /**
     * Get embedded sample data
     * @private
     * @returns {Object}
     */
    _getEmbeddedSample: function() {
      return {
        schema: 'topology_ai_output.v1',
        timestamp_utc: '2026-02-04T00:00:00Z',
        ai: { model: 'REIDCE v2', confidence: 0.91, status: 'Stable' },
        best: { name: 'baseline_topology_2', score: 0.82, tag: 'Stiffened' },
        system: { power_rails: 4, photonic_links: 3, thermal_nodes: 5 },
        cad: {
          quality: 'High Fidelity',
          triangle_count: 192,
          vertex_count: 98,
          mesh_score: 0.94,
          surface_area: 0.0063,
          wireframe: [
            { x1: -5, y1: 0, x2: 5, y2: 0 },
            { x1: 5, y1: 0, x2: 4.3, y2: 2.5 },
            { x1: 4.3, y1: 2.5, x2: 2.5, y2: 4.3 },
            { x1: 2.5, y1: 4.3, x2: 0, y2: 5 },
            { x1: 0, y1: 5, x2: -2.5, y2: 4.3 },
            { x1: -2.5, y1: 4.3, x2: -4.3, y2: 2.5 },
            { x1: -4.3, y1: 2.5, x2: -5, y2: 0 },
            { x1: -5, y1: 0, x2: -4.3, y2: -2.5 },
            { x1: -4.3, y1: -2.5, x2: -2.5, y2: -4.3 },
            { x1: -2.5, y1: -4.3, x2: 0, y2: -5 },
            { x1: 0, y1: -5, x2: 2.5, y2: -4.3 },
            { x1: 2.5, y1: -4.3, x2: 4.3, y2: -2.5 },
            { x1: 4.3, y1: -2.5, x2: 5, y2: 0 },
            { x1: -5, y1: 0, x2: -3, y2: 10 },
            { x1: 5, y1: 0, x2: 3, y2: 10 },
            { x1: 0, y1: 5, x2: 0, y2: 15 },
            { x1: 0, y1: -5, x2: 0, y2: 5 },
            { x1: -3, y1: 10, x2: 3, y2: 10 },
            { x1: 0, y1: 15, x2: -3, y2: 10 },
            { x1: 0, y1: 15, x2: 3, y2: 10 },
          ],
        },
        fea: {
          converged: true,
          max_displacement_m: 0.00012,
          max_von_mises_pa: 45200000,
          safety_factor: 5.53,
          element_stresses: [
            { id: 0, von_mises: 45.2 },
            { id: 1, von_mises: 40.8 },
            { id: 2, von_mises: 36.1 },
            { id: 3, von_mises: 31.5 },
            { id: 4, von_mises: 27.0 },
            { id: 5, von_mises: 22.3 },
            { id: 6, von_mises: 17.6 },
            { id: 7, von_mises: 12.9 },
            { id: 8, von_mises: 8.2 },
            { id: 9, von_mises: 3.5 },
          ],
          nodal_displacements: [
            { id: 0, ux: 0.0 },
            { id: 1, ux: 0.001 },
            { id: 2, ux: 0.004 },
            { id: 3, ux: 0.009 },
            { id: 4, ux: 0.016 },
            { id: 5, ux: 0.025 },
            { id: 6, ux: 0.036 },
            { id: 7, ux: 0.049 },
            { id: 8, ux: 0.064 },
            { id: 9, ux: 0.081 },
            { id: 10, ux: 0.12 },
          ],
        },
        flight: {
          target_altitude_m: 120,
          target_speed_m_s: 14,
          mode: 'Test Pilot',
          path: [
            { t: 0.0, alt: 10.0 },
            { t: 5.0, alt: 40.0 },
            { t: 10.0, alt: 85.0 },
            { t: 15.0, alt: 110.0 },
            { t: 20.0, alt: 120.0 },
          ],
        },
        thermal: {
          nodes: [
            { name: 'core', temp: 61.2 },
            { name: 'pmu', temp: 54.8 },
            { name: 'bus', temp: 49.6 },
            { name: 'optics', temp: 58.1 },
          ],
        },
        wind: { ship_efficiency: 0.62, kite_power_kw: 48, ship_force: [0, 22, 38, 54, 68] },
        sales: { gross_margin_usd: 1200000, shipping_cost_usd: 180000, revenue_usd: 3200000 },
        inspector: {
          processor: 'Photonic Core v2',
          bus_voltage: '16 V',
          thermal_margin: '+1.6 W',
          electro_thermal: 'Converged',
        },
      };
    },
  };

  // ============================================================================
  // UI CONTROLLER
  // ============================================================================

  const UIController = {
    /**
     * Set status badge
     * @param {string} text
     * @param {string} [tone='ready'] - One of: ready, info, warn, ok, fail, loading
     */
    setStatus: function(text, tone) {
      tone = tone || 'ready';
      DOMManager.setText('statusBadge', text);
      DOMManager.setAttr('statusBadge', 'data-tone', tone);
      Logger.debug(`Status: ${text} (${tone})`);
    },

    /**
     * Update clock display
     */
    updateClock: function() {
      const now = new Date();
      const timeStr = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      DOMManager.setText('clock', timeStr);
    },

    /**
     * Render payload data to UI
     * @param {Object} payload
     */
    renderPayload: function(payload) {
      try {
        // Validate payload
        const validation = Validator.validatePayload(payload);
        if (!validation.valid) {
          Logger.error('Invalid payload', validation.errors);
          this.setStatus('INVALID DATA', 'fail');
          return;
        }

        this.setStatus('LOADED', 'ok');

        // System
        DOMManager.setText('railCount', String(Validator.sanitizeNumber(payload.system?.power_rails, 4, 0)));
        DOMManager.setText('photonicLinks', String(Validator.sanitizeNumber(payload.system?.photonic_links, 3, 0)));
        DOMManager.setText('thermalNodes', String(Validator.sanitizeNumber(payload.system?.thermal_nodes, 5, 0)));

        // AI
        DOMManager.setText('aiBest', Validator.sanitizeString(payload.best?.name, 'baseline_topology_2'));
        DOMManager.setText('aiScore', Validator.sanitizeNumber(payload.best?.score, 0.82).toFixed(2));
        DOMManager.setText('aiRecommendation', Validator.sanitizeString(payload.best?.tag, 'Stiffened'));
        DOMManager.setText('aiModel', Validator.sanitizeString(payload.ai?.model, 'REIDCE v2'));
        DOMManager.setText('aiConfidence', Validator.sanitizeNumber(payload.ai?.confidence, 0.91).toFixed(2));
        DOMManager.setText('aiStatus', Validator.sanitizeString(payload.ai?.status, 'Stable'));

        // Inspector
        DOMManager.setText('processorLabel', Validator.sanitizeString(payload.inspector?.processor, 'Photonic Core v2'));
        DOMManager.setText('busVoltage', Validator.sanitizeString(payload.inspector?.bus_voltage, '16 V'));
        DOMManager.setText('thermalMargin', Validator.sanitizeString(payload.inspector?.thermal_margin, '+1.6 W'));
        DOMManager.setText('electroThermal', Validator.sanitizeString(payload.inspector?.electro_thermal, 'Converged'));

        // Flight
        DOMManager.setText('flightAlt', `${Validator.sanitizeNumber(payload.flight?.target_altitude_m, 120)} m`);
        DOMManager.setText('flightSpeed', `${Validator.sanitizeNumber(payload.flight?.target_speed_m_s, 14)} m/s`);
        DOMManager.setText('flightMode', Validator.sanitizeString(payload.flight?.mode, 'Test Pilot'));

        // Wind
        DOMManager.setText('shipEfficiency', Validator.sanitizeNumber(payload.wind?.ship_efficiency, 0.62).toFixed(2));
        DOMManager.setText('kitePower', `${Validator.sanitizeNumber(payload.wind?.kite_power_kw, 48)} kW`);

        // Sales
        const grossMargin = Validator.sanitizeNumber(payload.sales?.gross_margin_usd, 1200000);
        const shippingCost = Validator.sanitizeNumber(payload.sales?.shipping_cost_usd, 180000);
        DOMManager.setText('grossMargin', `$${this._formatNumber(grossMargin)}`);
        DOMManager.setText('shippingCost', `$${this._formatNumber(shippingCost)}`);

        // CAD
        const cad = payload.cad || {};
        DOMManager.setText('cadQuality', Validator.sanitizeString(cad.quality, 'High Fidelity'));
        DOMManager.setText('cadTriangles', String(Validator.sanitizeNumber(cad.triangle_count, 192, 0)));
        DOMManager.setText('cadVertices', String(Validator.sanitizeNumber(cad.vertex_count, 98, 0)));
        DOMManager.setText('cadMeshScore', Validator.sanitizeNumber(cad.mesh_score, 0.94, 0, 1).toFixed(2));
        DOMManager.setText('cadSurfaceArea', `${Validator.sanitizeNumber(cad.surface_area, 0.0063, 0).toFixed(4)} m²`);

        // FEA
        const fea = payload.fea || {};
        const maxDisp = Validator.sanitizeNumber(fea.max_displacement_m, 0.00012, 0);
        const maxStress = Validator.sanitizeNumber(fea.max_von_mises_pa, 45200000, 0);
        const safetyFactor = Validator.sanitizeNumber(fea.safety_factor, 5.53, 0);
        DOMManager.setText('feaMaxDisp', `${(maxDisp * 1000).toFixed(2)} mm`);
        DOMManager.setText('feaMaxStress', `${(maxStress / 1e6).toFixed(1)} MPa`);
        DOMManager.setText('feaSafetyFactor', safetyFactor.toFixed(2));
        DOMManager.setText('feaConverged', fea.converged ? 'Yes' : 'No');

        // Render canvases
        CanvasRenderer.drawCadWireframe(DOMManager.get('cadCanvas'), cad.wireframe || [], cad);
        CanvasRenderer.drawFEAStress(DOMManager.get('feaCanvas'), fea.element_stresses || []);
        CanvasRenderer.drawFEADisplacement(DOMManager.get('feaDispCanvas'), fea.nodal_displacements || []);
        CanvasRenderer.drawFlightPath(DOMManager.get('flightCanvas'), payload.flight?.path || []);
        CanvasRenderer.drawThermalBars(DOMManager.get('thermalCanvas'), payload.thermal?.nodes || []);
        CanvasRenderer.drawWindCurve(DOMManager.get('windCanvas'), payload.wind?.ship_force || []);
        CanvasRenderer.drawSalesBars(DOMManager.get('salesCanvas'), payload.sales || {});

        // Update status bars
        const meshQuality = Math.round(Validator.sanitizeNumber(cad.mesh_score, 0.94, 0, 1) * 100);
        const feaSafety = Math.min(100, Math.round((safetyFactor / 10) * 100));
        const aiConfidence = Math.round(Validator.sanitizeNumber(payload.ai?.confidence, 0.91, 0, 1) * 100);
        const windEfficiency = Math.round(Validator.sanitizeNumber(payload.wind?.ship_efficiency, 0.62, 0, 1) * 100);

        this._updateStatusBars({
          ai: aiConfidence,
          flight: 74,
          thermal: 67,
          wind: windEfficiency,
          mesh: meshQuality,
          fea: feaSafety,
        });

        Logger.info('Payload rendered successfully');
      } catch (err) {
        Logger.error('Error rendering payload', err);
        this.setStatus('RENDER ERROR', 'fail');
      }
    },

    /**
     * Export snapshot
     */
    exportSnapshot: function() {
      try {
        const snapshot = {
          rails: DOMManager.get('railCount')?.textContent,
          photonics: DOMManager.get('photonicLinks')?.textContent,
          thermal: DOMManager.get('thermalNodes')?.textContent,
          processor: DOMManager.get('processorLabel')?.textContent,
          bus: DOMManager.get('busVoltage')?.textContent,
          margin: DOMManager.get('thermalMargin')?.textContent,
          electroThermal: DOMManager.get('electroThermal')?.textContent,
          cad: {
            quality: DOMManager.get('cadQuality')?.textContent,
            triangles: DOMManager.get('cadTriangles')?.textContent,
            vertices: DOMManager.get('cadVertices')?.textContent,
            meshScore: DOMManager.get('cadMeshScore')?.textContent,
            surfaceArea: DOMManager.get('cadSurfaceArea')?.textContent,
          },
          fea: {
            maxDisplacement: DOMManager.get('feaMaxDisp')?.textContent,
            maxStress: DOMManager.get('feaMaxStress')?.textContent,
            safetyFactor: DOMManager.get('feaSafetyFactor')?.textContent,
            converged: DOMManager.get('feaConverged')?.textContent,
          },
          timestamp: new Date().toISOString(),
        };

        const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        link.download = `studio_snapshot_${timestamp}.json`;
        link.click();
        URL.revokeObjectURL(link.href);

        this.setStatus('EXPORTED', 'info');
        Logger.info('Snapshot exported');
      } catch (err) {
        Logger.error('Export failed', err);
        this.setStatus('EXPORT FAILED', 'fail');
      }
    },

    /**
     * @private
     */
    _formatNumber: function(value) {
      return new Intl.NumberFormat('en-US').format(value);
    },

    /**
     * @private
     */
    _updateStatusBars: function(values) {
      this._setBar('barAI', 'valAI', values.ai);
      this._setBar('barFlight', 'valFlight', values.flight);
      this._setBar('barThermal', 'valThermal', values.thermal);
      this._setBar('barWind', 'valWind', values.wind);
      this._setBar('barMesh', 'valMesh', values.mesh);
      this._setBar('barFEA', 'valFEA', values.fea);
    },

    /**
     * @private
     */
    _setBar: function(barKey, labelKey, value) {
      const bar = DOMManager.get(barKey);
      const label = DOMManager.get(labelKey);
      if (!bar || !label) return;

      const clamped = Math.max(0, Math.min(100, value || 0));
      bar.style.width = `${clamped}%`;
      label.textContent = `${clamped}%`;
    },
  };

  // ============================================================================
  // CANVAS RENDERER
  // ============================================================================

  const CanvasRenderer = {
    /**
     * Draw flight path
     * @param {HTMLCanvasElement|null} canvas
     * @param {Array} points
     */
    drawFlightPath: function(canvas, points) {
      if (!canvas || !Array.isArray(points) || points.length === 0) return;

      try {
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = 'rgba(56, 243, 255, 0.8)';
        ctx.lineWidth = 2;
        ctx.beginPath();

        points.forEach((point, idx) => {
          const x = (canvas.width - 20) * (idx / (points.length - 1)) + 10;
          const y = canvas.height - 20 - (canvas.height - 40) * ((point.alt || 0) / 130);
          if (idx === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        });

        ctx.stroke();
      } catch (err) {
        Logger.error('Error drawing flight path', err);
      }
    },

    /**
     * Draw thermal bars
     * @param {HTMLCanvasElement|null} canvas
     * @param {Array} nodes
     */
    drawThermalBars: function(canvas, nodes) {
      if (!canvas || !Array.isArray(nodes) || nodes.length === 0) return;

      try {
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const maxTemp = Math.max(...nodes.map(node => node.temp || 0));

        nodes.forEach((node, idx) => {
          const barWidth = (canvas.width - 30) / nodes.length;
          const temp = node.temp || 0;
          const height = maxTemp > 0 ? ((temp / maxTemp) * (canvas.height - 30)) : 0;
          const x = 10 + idx * barWidth;
          const y = canvas.height - height - 10;
          ctx.fillStyle = 'rgba(124, 92, 255, 0.7)';
          ctx.fillRect(x, y, barWidth * 0.6, height);
        });
      } catch (err) {
        Logger.error('Error drawing thermal bars', err);
      }
    },

    /**
     * Draw wind curve
     * @param {HTMLCanvasElement|null} canvas
     * @param {Array} series
     */
    drawWindCurve: function(canvas, series) {
      if (!canvas || !Array.isArray(series) || series.length === 0) return;

      try {
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = 'rgba(199, 125, 255, 0.8)';
        ctx.lineWidth = 2;
        ctx.beginPath();

        series.forEach((value, idx) => {
          const x = (canvas.width - 20) * (idx / (series.length - 1)) + 10;
          const y = canvas.height - 20 - (canvas.height - 40) * ((value || 0) / 80);
          if (idx === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        });

        ctx.stroke();
      } catch (err) {
        Logger.error('Error drawing wind curve', err);
      }
    },

    /**
     * Draw sales bars
     * @param {HTMLCanvasElement|null} canvas
     * @param {Object} sales
     */
    drawSalesBars: function(canvas, sales) {
      if (!canvas || !sales) return;

      try {
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const values = [
          sales.revenue_usd || 3200000,
          sales.gross_margin_usd || 1200000,
          sales.shipping_cost_usd || 180000,
        ];
        const colors = [
          'rgba(56, 243, 255, 0.7)',
          'rgba(124, 92, 255, 0.7)',
          'rgba(255, 120, 120, 0.6)',
        ];
        const maxVal = Math.max(...values);

        values.forEach((value, idx) => {
          const barWidth = (canvas.width - 30) / values.length;
          const height = maxVal > 0 ? ((value / maxVal) * (canvas.height - 30)) : 0;
          const x = 10 + idx * barWidth;
          const y = canvas.height - height - 10;
          ctx.fillStyle = colors[idx];
          ctx.fillRect(x, y, barWidth * 0.6, height);
        });
      } catch (err) {
        Logger.error('Error drawing sales bars', err);
      }
    },

    /**
     * Draw CAD wireframe
     * @param {HTMLCanvasElement|null} canvas
     * @param {Array} wireframe
     * @param {Object} cadData
     */
    drawCadWireframe: function(canvas, wireframe, cadData) {
      if (!canvas) return;

      try {
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        // Grid backdrop
        ctx.strokeStyle = 'rgba(56, 243, 255, 0.12)';
        ctx.lineWidth = 0.5;
        const gridStep = 20;
        for (let gx = 0; gx <= w; gx += gridStep) {
          ctx.beginPath();
          ctx.moveTo(gx, 0);
          ctx.lineTo(gx, h);
          ctx.stroke();
        }
        for (let gy = 0; gy <= h; gy += gridStep) {
          ctx.beginPath();
          ctx.moveTo(0, gy);
          ctx.lineTo(w, gy);
          ctx.stroke();
        }

        // Generate cylinder wireframe if no external data
        const edges = Array.isArray(wireframe) && wireframe.length > 0
          ? wireframe
          : this._generateCylinderWireframe(48);

        const cx = w / 2;
        const cy = h / 2;
        const scale = Math.min(w, h) / 40;

        // Draw wireframe edges with perspective glow
        ctx.lineWidth = 1.5;
        edges.forEach((edge, idx) => {
          const alpha = 0.3 + 0.5 * (idx / edges.length);
          ctx.strokeStyle = `rgba(56, 243, 255, ${alpha.toFixed(2)})`;
          ctx.beginPath();
          ctx.moveTo(cx + (edge.x1 || 0) * scale, cy - (edge.y1 || 0) * scale);
          ctx.lineTo(cx + (edge.x2 || 0) * scale, cy - (edge.y2 || 0) * scale);
          ctx.stroke();
        });

        // Draw vertices as dots
        ctx.fillStyle = 'rgba(124, 92, 255, 0.8)';
        edges.forEach(edge => {
          ctx.beginPath();
          ctx.arc(cx + (edge.x1 || 0) * scale, cy - (edge.y1 || 0) * scale, 2, 0, 2 * Math.PI);
          ctx.fill();
          ctx.beginPath();
          ctx.arc(cx + (edge.x2 || 0) * scale, cy - (edge.y2 || 0) * scale, 2, 0, 2 * Math.PI);
          ctx.fill();
        });

        // Labels
        ctx.fillStyle = 'rgba(56, 243, 255, 0.6)';
        ctx.font = '10px monospace';
        ctx.fillText('CAD: ' + (cadData.quality || 'High Fidelity'), 8, 14);
        ctx.fillText('Triangles: ' + (cadData.triangle_count || 192), 8, 26);
      } catch (err) {
        Logger.error('Error drawing CAD wireframe', err);
      }
    },

    /**
     * Draw FEA stress
     * @param {HTMLCanvasElement|null} canvas
     * @param {Array} stresses
     */
    drawFEAStress: function(canvas, stresses) {
      if (!canvas) return;

      try {
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const data = Array.isArray(stresses) && stresses.length > 0
          ? stresses
          : [
              { id: 0, von_mises: 45 }, { id: 1, von_mises: 40 }, { id: 2, von_mises: 36 },
              { id: 3, von_mises: 31 }, { id: 4, von_mises: 27 }, { id: 5, von_mises: 22 },
              { id: 6, von_mises: 17 }, { id: 7, von_mises: 13 }, { id: 8, von_mises: 8 },
              { id: 9, von_mises: 3 },
            ];

        const maxStress = Math.max(...data.map(d => d.von_mises || 0));
        const barWidth = (w - 30) / data.length;

        data.forEach((elem, idx) => {
          const ratio = maxStress > 0 ? (elem.von_mises || 0) / maxStress : 0;
          const barH = ratio * (h - 40);
          const x = 15 + idx * barWidth;
          const y = h - barH - 20;
          const r = Math.round(255 * ratio);
          const g = Math.round(100 * (1 - ratio));
          const b = Math.round(255 * (1 - ratio));
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.8)`;
          ctx.fillRect(x, y, barWidth * 0.7, barH);
        });

        ctx.fillStyle = 'rgba(56, 243, 255, 0.6)';
        ctx.font = '10px monospace';
        ctx.fillText('Von Mises (MPa)', 8, 14);
      } catch (err) {
        Logger.error('Error drawing FEA stress', err);
      }
    },

    /**
     * Draw FEA displacement
     * @param {HTMLCanvasElement|null} canvas
     * @param {Array} displacements
     */
    drawFEADisplacement: function(canvas, displacements) {
      if (!canvas) return;

      try {
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const data = Array.isArray(displacements) && displacements.length > 0
          ? displacements
          : [
              { id: 0, ux: 0 }, { id: 1, ux: 0.001 }, { id: 2, ux: 0.004 },
              { id: 3, ux: 0.009 }, { id: 4, ux: 0.016 }, { id: 5, ux: 0.025 },
              { id: 6, ux: 0.036 }, { id: 7, ux: 0.049 }, { id: 8, ux: 0.064 },
              { id: 9, ux: 0.081 }, { id: 10, ux: 0.12 },
            ];

        if (data.length === 0) return;

        const maxDisp = Math.max(...data.map(d => Math.abs(d.ux || 0)));

        // Draw undeformed beam (dashed)
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = 'rgba(160, 172, 200, 0.4)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(20, h / 2);
        ctx.lineTo(w - 20, h / 2);
        ctx.stroke();
        ctx.setLineDash([]);

        // Draw deformed beam
        ctx.strokeStyle = 'rgba(56, 243, 255, 0.9)';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        data.forEach((node, idx) => {
          const x = 20 + ((w - 40) * idx) / (data.length - 1);
          const yOffset = maxDisp > 0 ? ((node.ux || 0) / maxDisp) * (h / 2 - 30) : 0;
          const y = h / 2 - yOffset;
          if (idx === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        });
        ctx.stroke();

        // Draw nodes
        ctx.fillStyle = 'rgba(124, 92, 255, 0.9)';
        data.forEach((node, idx) => {
          const x = 20 + ((w - 40) * idx) / (data.length - 1);
          const yOffset = maxDisp > 0 ? ((node.ux || 0) / maxDisp) * (h / 2 - 30) : 0;
          const y = h / 2 - yOffset;
          ctx.beginPath();
          ctx.arc(x, y, 3, 0, 2 * Math.PI);
          ctx.fill();
        });

        // Fixed support indicator
        ctx.fillStyle = 'rgba(255, 120, 120, 0.6)';
        ctx.fillRect(10, h / 2 - 15, 10, 30);

        ctx.fillStyle = 'rgba(56, 243, 255, 0.6)';
        ctx.font = '10px monospace';
        ctx.fillText('Displacement (exaggerated)', 8, 14);
      } catch (err) {
        Logger.error('Error drawing FEA displacement', err);
      }
    },

    /**
     * @private
     */
    _generateCylinderWireframe: function(segments) {
      const edges = [];
      const radius = 5;
      const height = 15;
      const skewX = 0.3;
      const skewY = 0.15;

      for (let i = 0; i < segments; i++) {
        const a1 = (2 * Math.PI * i) / segments;
        const a2 = (2 * Math.PI * ((i + 1) % segments)) / segments;
        const bx1 = radius * Math.cos(a1);
        const by1 = radius * Math.sin(a1) * 0.4;
        const bx2 = radius * Math.cos(a2);
        const by2 = radius * Math.sin(a2) * 0.4;

        edges.push({ x1: bx1, y1: by1 - height / 2, x2: bx2, y2: by2 - height / 2 });

        const tx1 = bx1 + skewX * height;
        const ty1 = by1 + height / 2 + skewY * height;
        const tx2 = bx2 + skewX * height;
        const ty2 = by2 + height / 2 + skewY * height;

        edges.push({ x1: tx1, y1: ty1, x2: tx2, y2: ty2 });

        if (i % 4 === 0) {
          edges.push({ x1: bx1, y1: by1 - height / 2, x2: tx1, y2: ty1 });
        }
      }

      return edges;
    },
  };

  // ============================================================================
  // APPLICATION
  // ============================================================================

  const App = {
    /**
     * Initialize application
     */
    init: function() {
      Logger.info('Initializing V2 Studio');

      try {
        // Initialize managers
        DOMManager.init();

        // Subscribe to state changes
        StateManager.subscribe(payload => {
          UIController.renderPayload(payload);
        });

        // Set up event listeners
        const btnLoadSample = DOMManager.get('btnLoadSample');
        const btnExport = DOMManager.get('btnExport');

        if (btnLoadSample) {
          btnLoadSample.addEventListener('click', () => this.loadSample());
        }

        if (btnExport) {
          btnExport.addEventListener('click', () => UIController.exportSnapshot());
        }

        // Start clock
        UIController.updateClock();
        setInterval(() => UIController.updateClock(), CONFIG.clockUpdateInterval);

        UIController.setStatus('READY', 'ready');
        Logger.info('V2 Studio initialized successfully');
      } catch (err) {
        Logger.error('Initialization failed', err);
        UIController.setStatus('INIT FAILED', 'fail');
      }
    },

    /**
     * Load sample data
     */
    loadSample: function() {
      UIController.setStatus('LOADING', 'loading');

      DataLoader.loadSample()
        .then(payload => {
          StateManager.setPayload(payload);
        })
        .catch(err => {
          Logger.error('Failed to load sample', err);
          UIController.setStatus('LOAD FAILED', 'fail');
        });
    },
  };

  // ============================================================================
  // INITIALIZE ON DOM READY
  // ============================================================================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => App.init());
  } else {
    App.init();
  }

})();
