/**
 * RMS Work Assistant - Service Worker
 *
 * Handles:
 * - WebSocket connection to Python agent server
 * - Message routing between sidepanel and content scripts
 * - Tab state management
 * - Screenshot capture
 * - Browser action handling
 */

// Configuration
const CONFIG = {
  wsUrl: 'ws://localhost:8765',
  reconnectDelay: 3000
};

// State
let ws = null;
let sidePanelPort = null;

// ============================================================================
// SIDE PANEL MANAGEMENT
// ============================================================================

// Open side panel when extension icon is clicked
chrome.action.onClicked.addListener(async (tab) => {
  await chrome.sidePanel.open({ tabId: tab.id });
});

// Set side panel behavior
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

// ============================================================================
// WEBSOCKET CONNECTION
// ============================================================================

function connectWebSocket() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    return;
  }

  console.log('[RMS SW] Connecting to agent server...');

  try {
    ws = new WebSocket(CONFIG.wsUrl);

    ws.onopen = () => {
      console.log('[RMS SW] Connected to agent server');
      broadcastToSidePanel({ type: 'CONNECTION_STATUS', connected: true });
    };

    ws.onclose = () => {
      console.log('[RMS SW] Disconnected from agent server');
      broadcastToSidePanel({ type: 'CONNECTION_STATUS', connected: false });
      ws = null;

      // Attempt reconnect
      setTimeout(connectWebSocket, CONFIG.reconnectDelay);
    };

    ws.onerror = (error) => {
      console.error('[RMS SW] WebSocket error:', error);
    };

    ws.onmessage = (event) => {
      handleAgentMessage(JSON.parse(event.data));
    };
  } catch (error) {
    console.error('[RMS SW] Failed to create WebSocket:', error);
    setTimeout(connectWebSocket, CONFIG.reconnectDelay);
  }
}

function sendToAgent(message) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
    return true;
  }
  return false;
}

// ============================================================================
// MESSAGE HANDLING
// ============================================================================

async function handleAgentMessage(data) {
  console.log('[RMS SW] Agent message:', data);

  switch (data.type) {
    // Pass through to side panel
    case 'response_start':
    case 'response_chunk':
    case 'response_end':
    case 'tool_call':
    case 'tool_result':
    case 'action_request':
    case 'error':
      broadcastToSidePanel(data);
      break;

    // Execute browser actions
    case 'browser_action':
      const result = await executeBrowserAction(data);
      sendToAgent({ type: 'browser_action_result', actionId: data.actionId, result });
      break;
  }
}

// ============================================================================
// BROWSER ACTIONS
// ============================================================================

async function executeBrowserAction(action) {
  console.log('[RMS SW] Executing browser action:', action);

  try {
    switch (action.action) {
      case 'navigate':
        return await navigateToUrl(action.url);

      case 'screenshot':
        return await captureScreenshot();

      case 'get_tab_state':
        return await getTabState();

      case 'execute_script':
        return await executeInTab(action.script);

      case 'click':
        return await clickElement(action.selector);

      case 'fill':
        return await fillField(action.selector, action.value);

      case 'get_page_state':
        return await getPageState();

      default:
        return { success: false, error: `Unknown action: ${action.action}` };
    }
  } catch (error) {
    console.error('[RMS SW] Browser action error:', error);
    return { success: false, error: error.message };
  }
}

async function navigateToUrl(url) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    await chrome.tabs.update(tab.id, { url });
    return { success: true, tabId: tab.id };
  }
  return { success: false, error: 'No active tab' };
}

async function captureScreenshot() {
  try {
    const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'png' });
    return { success: true, screenshot: dataUrl };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function getTabState() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    return {
      success: true,
      tab: {
        id: tab.id,
        url: tab.url,
        title: tab.title
      }
    };
  }
  return { success: false, error: 'No active tab' };
}

async function executeInTab(script) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: new Function(script)
    });
    return { success: true, result: results[0]?.result };
  }
  return { success: false, error: 'No active tab' };
}

async function clickElement(selector) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (sel) => {
        const el = document.querySelector(sel);
        if (el) {
          el.click();
          return { success: true };
        }
        return { success: false, error: 'Element not found' };
      },
      args: [selector]
    });
    return results[0]?.result || { success: false, error: 'Script execution failed' };
  }
  return { success: false, error: 'No active tab' };
}

async function fillField(selector, value) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (sel, val) => {
        const el = document.querySelector(sel);
        if (el) {
          // Use native value setter for frameworks like ExtJS
          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
          ).set;
          nativeInputValueSetter.call(el, val);

          // Dispatch events
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          return { success: true };
        }
        return { success: false, error: 'Element not found' };
      },
      args: [selector, value]
    });
    return results[0]?.result || { success: false, error: 'Script execution failed' };
  }
  return { success: false, error: 'No active tab' };
}

async function getPageState() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        // Get key interactive elements
        const inputs = Array.from(document.querySelectorAll('input, select, textarea, button'))
          .slice(0, 50)  // Limit to first 50
          .map(el => ({
            tag: el.tagName.toLowerCase(),
            type: el.type,
            name: el.name,
            id: el.id,
            placeholder: el.placeholder,
            value: el.value?.substring(0, 100),  // Truncate values
            text: el.textContent?.substring(0, 50)
          }));

        return {
          url: window.location.href,
          title: document.title,
          elements: inputs
        };
      }
    });
    return { success: true, pageState: results[0]?.result };
  }
  return { success: false, error: 'No active tab' };
}

// ============================================================================
// COMMUNICATION
// ============================================================================

function broadcastToSidePanel(message) {
  // Send to any connected side panel
  chrome.runtime.sendMessage(message).catch(() => {
    // Side panel might not be open, that's okay
  });
}

// Listen for messages from side panel and content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[RMS SW] Received message:', message);

  switch (message.type) {
    case 'SEND_TO_AGENT':
      const sent = sendToAgent(message.data);
      sendResponse({ success: sent });
      break;

    case 'GET_CONNECTION_STATUS':
      sendResponse({ connected: ws && ws.readyState === WebSocket.OPEN });
      break;

    case 'CAPTURE_SCREENSHOT':
      captureScreenshot().then(result => sendResponse(result));
      return true;  // Keep channel open for async response

    case 'GET_TAB_STATE':
      getTabState().then(result => sendResponse(result));
      return true;

    case 'GET_PAGE_STATE':
      getPageState().then(result => sendResponse(result));
      return true;
  }
});

// Track tab changes and notify side panel
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  broadcastToSidePanel({
    type: 'TAB_STATE_UPDATE',
    tab: { id: tab.id, url: tab.url, title: tab.title }
  });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete') {
    broadcastToSidePanel({
      type: 'TAB_STATE_UPDATE',
      tab: { id: tab.id, url: tab.url, title: tab.title }
    });
  }
});

// ============================================================================
// INITIALIZATION
// ============================================================================

console.log('[RMS SW] Service worker starting...');
connectWebSocket();
