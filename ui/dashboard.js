const base = new URL('.', window.location.href);
const schemaUrl = new URL('../schemas/engine_output.schema.json', base);
const payloadUrl = new URL('./sample_payloads/sample_engine_output.json', base);
const invalidPayloadUrl = new URL('./sample_payloads/invalid_engine_output.json', base);

const elements = {
  diagnostics: document.getElementById('diagnostics'),
  status: document.getElementById('status'),
  payloadFile: document.getElementById('payloadFile'),
  loadSample: document.getElementById('loadSample'),
  loadInvalid: document.getElementById('loadInvalid'),
  validationStatus: document.getElementById('validationStatus'),
  schemaVersion: document.getElementById('schemaVersion'),
  runId: document.getElementById('runId'),
  determinism: document.getElementById('determinism'),
  markers: document.getElementById('markers'),
  missingFields: document.getElementById('missingFields'),
  summary: document.getElementById('summary'),
  metrics: document.getElementById('metrics'),
  artifacts: document.getElementById('artifacts'),
  errorList: document.getElementById('errorList'),
};

const state = {
  schema: null,
  ajv: null,
  schemaFetchResult: null,
};

function updateStatus(message, isValid = false) {
  elements.status.textContent = message;
  elements.status.className = `status__card ${isValid ? 'success' : 'failure'}`;
}

function renderDiagnostics(details) {
  const schemaResult = details?.schemaFetch ?? state.schemaFetchResult;
  const lines = [
    `<strong>Base URL:</strong> ${base.href}`,
    `<strong>Schema URL:</strong> ${schemaUrl.href}`,
    `<strong>Sample payload URL:</strong> ${payloadUrl.href}`,
  ];

  if (schemaResult) {
    lines.push(renderFetchResult('Schema fetch', schemaResult));
  }
  if (details?.payloadFetch) {
    lines.push(renderFetchResult('Payload fetch', details.payloadFetch));
  }

  elements.diagnostics.innerHTML = `
    <h2>Diagnostics</h2>
    <ul class="diagnostics">
      ${lines.map((line) => `<li>${line}</li>`).join('')}
    </ul>
  `;
}

function renderFetchResult(label, result) {
  const snippet = result.snippet
    ? `<details><summary>Response snippet</summary><pre>${escapeHtml(result.snippet)}</pre></details>`
    : '';
  return `${label}: status ${result.status ?? 'n/a'} (${result.statusText ?? 'n/a'}), content-type ${
    result.contentType ?? 'unknown'
  }${snippet}`;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderErrorPanel(title, error) {
  const suggestions = [];
  if (error?.url && error.url.includes('://') && error.url.includes('/schemas/')) {
    suggestions.push('Ensure the schema path is relative to the ui/ directory (../schemas/engine_output.schema.json).');
  }
  if (error?.contentType?.includes('text/html')) {
    suggestions.push('HTML was returned instead of JSON. Confirm the URL is correct and not a 404 page.');
    suggestions.push('GitHub Preview does not serve raw JSON. Use ui/dashboard_preview.html for PR previews.');
  }
  if (error?.status === 404) {
    suggestions.push('Resource returned 404. Check that the file exists and that the server root is correct.');
  }
  if (!error?.status) {
    suggestions.push('If viewing this file in GitHub Preview, open ui/dashboard_preview.html instead.');
  }

  const suggestionHtml = suggestions.length
    ? `<ul>${suggestions.map((item) => `<li>${item}</li>`).join('')}</ul>`
    : '<p>No automated suggestions available. Check network and file paths.</p>';

  elements.status.innerHTML = `
    <div class="error-panel">
      <h2>${title}</h2>
      <p><strong>URL:</strong> ${error?.url ?? 'n/a'}</p>
      <p><strong>Status:</strong> ${error?.status ?? 'n/a'} ${error?.statusText ?? ''}</p>
      <p><strong>Content-Type:</strong> ${error?.contentType ?? 'unknown'}</p>
      ${error?.snippet ? `<pre>${escapeHtml(error.snippet)}</pre>` : ''}
      <h3>Suggested fixes</h3>
      ${suggestionHtml}
    </div>
  `;
}

function initializeValidator() {
  if (!window.Ajv) {
    updateStatus('Validation unavailable (Ajv missing).', false);
    return null;
  }
  return new window.Ajv({ allErrors: true, strict: false });
}

function updateTrustSignals(payload) {
  elements.schemaVersion.textContent = payload.schema_version || '—';
  elements.runId.textContent = payload.run_id || '—';
  elements.determinism.textContent =
    payload.determinism && typeof payload.determinism.is_deterministic === 'boolean'
      ? payload.determinism.is_deterministic
        ? 'Deterministic'
        : 'Non-deterministic'
      : '—';
  elements.markers.textContent = Array.isArray(payload.determinism?.markers)
    ? payload.determinism.markers.join(', ') || 'None'
    : '—';
}

function renderKeyValue(target, data) {
  if (!data || typeof data !== 'object') {
    target.innerHTML = '<p>No data.</p>';
    return;
  }
  const items = Object.entries(data)
    .map(([key, value]) => `<div class="kv"><strong>${key}</strong><div>${String(value)}</div></div>`)
    .join('');
  target.innerHTML = items || '<p>No data.</p>';
}

function renderErrors(errors) {
  if (!errors || errors.length === 0) {
    elements.errorList.innerHTML = '<li>No errors to report.</li>';
    return;
  }
  elements.errorList.innerHTML = errors.map((error) => `<li>${escapeHtml(error.message ?? String(error))}</li>`).join('');
}

function renderMissingFields(errors) {
  const missing = errors
    .filter((error) => error.keyword === 'required')
    .map((error) => error.params?.missingProperty)
    .filter(Boolean);

  if (missing.length === 0) {
    elements.missingFields.innerHTML = '<li>No missing required fields.</li>';
    return;
  }
  elements.missingFields.innerHTML = missing.map((field) => `<li>${escapeHtml(field)}</li>`).join('');
}

function renderPayload(payload) {
  updateTrustSignals(payload);
  renderKeyValue(elements.summary, payload.summary);
  renderKeyValue(elements.metrics, payload.metrics);
  renderKeyValue(elements.artifacts, payload.artifacts);
}

async function fetchWithDiagnostics(url) {
  let response;
  try {
    response = await fetch(url);
  } catch (error) {
    return {
      ok: false,
      url: url.href,
      status: null,
      statusText: String(error),
      contentType: null,
      snippet: null,
    };
  }

  const contentType = response.headers.get('content-type');
  const text = await response.text();
  const snippet = text.slice(0, 300);

  return {
    ok: response.ok,
    url: response.url,
    status: response.status,
    statusText: response.statusText,
    contentType,
    snippet,
    bodyText: text,
  };
}

async function loadSchema() {
  const result = await fetchWithDiagnostics(schemaUrl);
  state.schemaFetchResult = result;
  renderDiagnostics({ schemaFetch: result });
  if (!result.ok) {
    renderErrorPanel('Schema fetch failed', result);
    return null;
  }
  if (result.contentType && result.contentType.includes('text/html')) {
    renderErrorPanel('Schema fetch returned HTML', result);
    return null;
  }
  try {
    return JSON.parse(result.bodyText);
  } catch (error) {
    renderErrorPanel('Schema JSON parse failed', { ...result, statusText: String(error) });
    return null;
  }
}

async function loadPayload(url) {
  const result = await fetchWithDiagnostics(url);
  renderDiagnostics({ payloadFetch: result });
  if (!result.ok) {
    renderErrorPanel('Payload fetch failed', result);
    return null;
  }
  if (result.contentType && result.contentType.includes('text/html')) {
    renderErrorPanel('Payload fetch returned HTML', result);
    return null;
  }
  try {
    return JSON.parse(result.bodyText);
  } catch (error) {
    renderErrorPanel('Payload JSON parse failed', { ...result, statusText: String(error) });
    return null;
  }
}

async function validateAndRender(payload) {
  if (!state.ajv || !state.schema) {
    updateStatus('Schema validation unavailable.', false);
    return;
  }
  const validate = state.ajv.compile(state.schema);
  const valid = validate(payload);
  updateStatus(valid ? 'Validation passed' : 'Validation failed', valid);
  renderErrors(validate.errors || []);
  renderMissingFields(validate.errors || []);
  renderPayload(payload);
}

async function initialize() {
  renderDiagnostics();
  state.ajv = initializeValidator();
  state.schema = await loadSchema();
  if (!state.schema) {
    return;
  }
  const payload = await loadPayload(payloadUrl);
  if (!payload) {
    return;
  }
  await validateAndRender(payload);
}

elements.loadSample.addEventListener('click', async () => {
  const payload = await loadPayload(payloadUrl);
  if (payload) {
    await validateAndRender(payload);
  }
});

elements.loadInvalid.addEventListener('click', async () => {
  const payload = await loadPayload(invalidPayloadUrl);
  if (payload) {
    await validateAndRender(payload);
  }
});

elements.payloadFile.addEventListener('change', async (event) => {
  const file = event.target.files[0];
  if (!file) {
    return;
  }
  try {
    const text = await file.text();
    const payload = JSON.parse(text);
    await validateAndRender(payload);
  } catch (error) {
    renderErrorPanel('Local payload parse failed', {
      url: file.name,
      statusText: String(error),
      contentType: file.type,
    });
  }
});

window.addEventListener('error', (event) => {
  renderErrorPanel('Unhandled error', {
    url: event.filename,
    statusText: event.message,
  });
});

window.addEventListener('unhandledrejection', (event) => {
  renderErrorPanel('Unhandled promise rejection', {
    url: 'Promise rejection',
    statusText: String(event.reason),
  });
});

initialize();
