/**
 * RMS Work Assistant - Service Worker
 *
 * Handles:
 * - Browser action execution (navigation, clicks, fills, screenshots)
 * - Tab state management
 * - Side panel management
 *
 * NOTE: WebSocket connection is handled by sidepanel.js
 * Browser actions are forwarded via chrome.runtime.sendMessage
 */

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

      case 'get_specific_tab_state':
        return await getSpecificTabState(action.tab_id);

      case 'execute_script':
        return await executeInTab(action.script);

      case 'click':
        return await clickElement(action.selector);

      case 'fill':
        return await fillField(action.selector, action.value);

      case 'get_page_state':
        return await getPageState();

      case 'select_option':
        return await selectOption(action.selector, action.value);

      case 'click_radio':
        return await clickRadio(action.label_contains);

      case 'fill_search':
        return await fillSearch(action.selector, action.value, action.select_first);

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

async function getSpecificTabState(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    return {
      success: true,
      tab: {
        id: tab.id,
        url: tab.url,
        title: tab.title
      }
    };
  } catch (error) {
    return { success: false, error: `Tab ${tabId} not found: ${error.message}` };
  }
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

async function selectOption(selector, value) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (sel, val) => {
        // Try multiple selectors
        const selectors = sel.split(',').map(s => s.trim());
        let select = null;

        for (const s of selectors) {
          select = document.querySelector(s);
          if (select) break;
        }

        if (!select) {
          return { success: false, error: 'Select element not found' };
        }

        // Try to select by value first, then by text
        let found = false;
        for (const option of select.options) {
          if (option.value === val || option.text.toUpperCase().includes(val.toUpperCase())) {
            select.value = option.value;
            found = true;
            break;
          }
        }

        if (found) {
          select.dispatchEvent(new Event('change', { bubbles: true }));
          return { success: true };
        }

        return { success: false, error: `Option '${val}' not found in select` };
      },
      args: [selector, value]
    });
    return results[0]?.result || { success: false, error: 'Script execution failed' };
  }
  return { success: false, error: 'No active tab' };
}

async function clickRadio(labelContains) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (labelText) => {
        // Find all labels and radio buttons
        const labels = Array.from(document.querySelectorAll('label'));
        const searchText = labelText.toLowerCase();

        for (const label of labels) {
          if (label.textContent.toLowerCase().includes(searchText)) {
            // Try to find associated radio
            const radio = label.querySelector('input[type="radio"]') ||
                          document.getElementById(label.getAttribute('for'));
            if (radio) {
              radio.click();
              return { success: true, clicked: label.textContent.trim() };
            }

            // If no radio found in label, click the label itself
            label.click();
            return { success: true, clicked: label.textContent.trim() };
          }
        }

        // Also try finding radio by adjacent text
        const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
        for (const radio of radios) {
          const parent = radio.parentElement;
          if (parent && parent.textContent.toLowerCase().includes(searchText)) {
            radio.click();
            return { success: true, clicked: parent.textContent.trim() };
          }
        }

        return { success: false, error: `Radio with label containing '${labelText}' not found` };
      },
      args: [labelContains]
    });
    return results[0]?.result || { success: false, error: 'Script execution failed' };
  }
  return { success: false, error: 'No active tab' };
}

async function fillSearch(selector, value, selectFirst = true) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (sel, val, autoSelect) => {
        // Try multiple selectors
        const selectors = sel.split(',').map(s => s.trim());
        let input = null;

        for (const s of selectors) {
          input = document.querySelector(s);
          if (input) break;
        }

        if (!input) {
          return { success: false, error: 'Search input not found' };
        }

        // Focus and fill the input
        input.focus();

        // Use native setter
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype, 'value'
        ).set;
        nativeInputValueSetter.call(input, val);

        // Dispatch events to trigger autocomplete
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('keyup', { bubbles: true }));

        // If autoSelect, try to click first result after a delay
        if (autoSelect) {
          setTimeout(() => {
            // Look for autocomplete dropdown
            const suggestions = document.querySelectorAll(
              '.autocomplete-item, .suggestion, .dropdown-item, [role="option"], ' +
              '.typeahead-result, .ui-menu-item, [class*="suggestion"], [class*="autocomplete"]'
            );
            if (suggestions.length > 0) {
              suggestions[0].click();
            }
          }, 500);
        }

        return { success: true };
      },
      args: [selector, value, selectFirst]
    });
    return results[0]?.result || { success: false, error: 'Script execution failed' };
  }
  return { success: false, error: 'No active tab' };
}

// ============================================================================
// COMMUNICATION
// ============================================================================

// Cache latest page context per tab
const pageContextCache = new Map();

// Listen for messages from content scripts and side panel
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[RMS SW] Received message:', message.type);

  switch (message.type) {
    case 'CAPTURE_SCREENSHOT':
      captureScreenshot().then(result => sendResponse(result));
      return true;  // Keep channel open for async response

    case 'GET_TAB_STATE':
      getTabState().then(result => sendResponse(result));
      return true;

    case 'GET_PAGE_STATE':
      getPageState().then(result => sendResponse(result));
      return true;

    case 'EXECUTE_BROWSER_ACTION':
      // Execute browser action forwarded from sidepanel
      console.log('[RMS SW] Executing browser action:', message.action?.action);
      executeBrowserAction(message.action).then(result => {
        console.log('[RMS SW] Browser action result:', result);
        sendResponse(result);
      });
      return true;  // Keep channel open for async response

    case 'PAGE_CONTEXT_UPDATE':
      // Route context updates from page-watcher to sidepanel
      console.log('[RMS SW] Page context update:', message.site, message.companyName || message.carrierName || '');

      // Cache the context for this tab
      if (sender.tab?.id) {
        pageContextCache.set(sender.tab.id, message);
      }

      // Forward to sidepanel
      chrome.runtime.sendMessage({
        type: 'PAGE_CONTEXT_UPDATE',
        ...message,
        tabId: sender.tab?.id
      }).catch(() => {
        // Side panel might not be open
      });
      return false;

    case 'GET_CACHED_CONTEXT':
      // Return cached context for a tab
      const cachedContext = pageContextCache.get(message.tabId);
      sendResponse({ success: true, context: cachedContext || null });
      return true;
  }
});

// Track tab changes and notify side panel
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  chrome.runtime.sendMessage({
    type: 'TAB_STATE_UPDATE',
    tab: { id: tab.id, url: tab.url, title: tab.title }
  }).catch(() => {
    // Side panel might not be open, that's okay
  });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete') {
    chrome.runtime.sendMessage({
      type: 'TAB_STATE_UPDATE',
      tab: { id: tab.id, url: tab.url, title: tab.title }
    }).catch(() => {
      // Side panel might not be open, that's okay
    });
  }
});

// ============================================================================
// INITIALIZATION
// ============================================================================

console.log('[RMS SW] Service worker ready (no WebSocket - sidepanel handles connection)');
