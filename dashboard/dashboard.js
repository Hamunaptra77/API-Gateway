const services = [
  { name: 'Terminal', path: '/api/terminals/health' },
  { name: 'Memory', path: '/api/memory/health' },
  { name: 'Vector Memory', path: '/api/vector/health' },
  { name: 'Filesystem', path: '/api/filesystem/health' },
  { name: 'Summarizer', path: '/api/summarizer/health' },
];

const gatewayStatusEl = document.getElementById('gatewayStatus');
const gatewayInfoEl = document.getElementById('gatewayInfo');
const gatewayUrlEl = document.getElementById('gatewayUrl');
const apiInfoEl = document.getElementById('apiInfo');
const servicesEl = document.getElementById('services');
const functionsEl = document.getElementById('functions');
const refreshButton = document.getElementById('refreshButton');

function statusClass(status) {
  if (status === 'healthy') return 'success';
  if (status === 'warning') return 'warning';
  return 'error';
}

function createServiceCard(service) {
  const card = document.createElement('section');
  card.className = 'card service-card';
  card.id = `service-${service.name.toLowerCase().replace(/\s+/g, '-')}`;

  const header = document.createElement('header');
  header.innerHTML = `<h3>${service.name}</h3><span id="status-${service.name}">Lade...</span>`;

  const pathLine = document.createElement('div');
  pathLine.className = 'status-row';
  pathLine.innerHTML = `<span>Gateway Pfad:</span><code>${service.path}</code>`;

  const responseLine = document.createElement('div');
  responseLine.className = 'status-row';
  responseLine.innerHTML = `<span>Antwort:</span><strong id="response-${service.name}">-</strong>`;

  const messageLine = document.createElement('div');
  messageLine.className = 'status-row';
  messageLine.innerHTML = `<span>Hinweis:</span><strong id="message-${service.name}">-</strong>`;

  card.appendChild(header);
  card.appendChild(pathLine);
  card.appendChild(responseLine);
  card.appendChild(messageLine);

  return card;
}

function updateServiceCard(service, state) {
  const statusEl = document.getElementById(`status-${service.name}`);
  const responseEl = document.getElementById(`response-${service.name}`);
  const messageEl = document.getElementById(`message-${service.name}`);

  statusEl.textContent = state.label;
  statusEl.className = statusClass(state.status);
  responseEl.textContent = `${state.code} ${state.statusText}`;
  messageEl.textContent = state.message;
}

function getApiKey() {
  return sessionStorage.getItem('apiKey');
}

function setApiKey(key) {
  sessionStorage.setItem('apiKey', key);
  apiKeyMessage.textContent = 'API-Key gespeichert.';
}

function loadApiKeyFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const apiKey = params.get('api_key');
  if (apiKey) {
    setApiKey(apiKey);
  }
}

async function fetchJson(path) {
  const headers = {};
  const apiKey = getApiKey();
  if (apiKey) {
    headers['x-api-key'] = apiKey;
  }
  return fetch(path, { cache: 'no-store', headers });
}

async function refreshDashboard() {
  gatewayStatusEl.textContent = 'Lade...';
  gatewayStatusEl.className = '';
  gatewayInfoEl.textContent = '-';
  apiInfoEl.textContent = 'Lade...';

  try {
    const healthRes = await fetchJson('/health');
    const healthy = healthRes.ok;
    gatewayStatusEl.textContent = healthy ? 'HEALTHY' : 'UNHEALTHY';
    gatewayStatusEl.className = statusClass(healthy ? 'healthy' : 'error');
    gatewayUrlEl.textContent = '/health';
  } catch (error) {
    gatewayStatusEl.textContent = 'FEHLER';
    gatewayStatusEl.className = statusClass('error');
    gatewayUrlEl.textContent = '/health';
  }

  try {
    const infoRes = await fetchJson('/api-info');
    const infoJson = await infoRes.json();
    apiInfoEl.textContent = JSON.stringify(infoJson, null, 2);
    gatewayInfoEl.textContent = infoJson.gateway ? infoJson.gateway : 'API Gateway aktiv';
  } catch (error) {
    apiInfoEl.textContent = `Fehler beim Laden der Gateway-Info:\n${error}. Bitte API-Key speichern.`;
    gatewayInfoEl.textContent = 'Info nicht verfügbar';
  }

  const apiKey = getApiKey();
  if (!apiKey) {
    // Wenn kein API-Key gesetzt, Service-Checks überspringen
    for (const service of services) {
      updateServiceCard(service, {
        status: 'warning',
        label: 'API-Key erforderlich',
        code: '-',
        statusText: 'nicht geprüft',
        message: 'Bitte API-Key eingeben und speichern',
      });
    }
  } else {
    // Service-Checks nur mit API-Key
    for (const service of services) {
      const defaultState = {
        status: 'error',
        label: 'Fehler',
        code: '-',
        statusText: 'nicht verfügbar',
        message: 'Service konnte nicht geprüft werden',
      };

      try {
        const res = await fetchJson(service.path);
        const reachable = res.ok || [401, 403].includes(res.status);
        let statusLabel = reachable ? 'OK' : 'Fehler';
        let message = reachable ? 'Service erreichbar' : 'HTTP Fehler';

        if (res.status === 503) {
          statusLabel = 'Circuit Breaker';
          message = 'Service temporär nicht verfügbar';
        } else if (res.status === 502) {
          statusLabel = 'Bad Gateway';
          message = 'Upstream-Fehler';
        } else if (res.status === 429) {
          statusLabel = 'Rate Limit';
          message = 'Zu viele Anfragen';
        } else if (res.status === 401) {
          statusLabel = 'Auth Fehler';
          message = 'API-Key ungültig';
        }

        updateServiceCard(service, {
          status: reachable ? 'healthy' : 'error',
          label: statusLabel,
          code: res.status,
          statusText: res.statusText,
          message: message,
        });
      } catch (error) {
        updateServiceCard(service, {
          ...defaultState,
          message: error.message,
        });
      }
    }
  }

  await refreshFunctions();
}

function formatRoute(route) {
  return `${route.path} [${route.methods.join(', ')}] => ${route.endpoint}${route.summary ? ` — ${route.summary}` : ''}`;
}

function formatHelper(helper) {
  return `${helper.name}${helper.line ? ` (Zeile ${helper.line})` : ''}${helper.doc ? `\n${helper.doc}` : ''}`;
}

async function refreshFunctions() {
  try {
    const res = await fetchJson('/api/functions');
    const data = await res.json();

    const routes = data.routes.map(formatRoute).join('\n');
    const helpers = data.helpers.map(formatHelper).join('\n\n');

    functionsEl.innerHTML = `
      <h3>Routing-Funktionen</h3>
      <pre>${routes}</pre>
      <h3>Hilfsfunktionen</h3>
      <pre>${helpers}</pre>
    `;
  } catch (error) {
    functionsEl.textContent = `Fehler beim Laden der Funktionen: ${error}`;
  }
}

function initDashboard() {
  for (const service of services) {
    servicesEl.appendChild(createServiceCard(service));
  }

  saveApiKeyButton.addEventListener('click', () => {
    const key = apiKeyInput.value.trim();
    if (key) {
      setApiKey(key);
    }
  });

  loadApiKeyFromQuery();
  const storedKey = getApiKey();
  if (storedKey) {
    apiKeyInput.value = storedKey;
  }

  refreshButton.addEventListener('click', refreshDashboard);
  refreshDashboard();
}

window.addEventListener('DOMContentLoaded', initDashboard);
