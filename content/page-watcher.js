/**
 * Page Watcher - Real-time DOM awareness for RMS Assistant
 *
 * Monitors page changes and reports context to the extension.
 * Semi-active: Shows context + suggests actions, doesn't auto-fetch.
 */

// Site detection patterns
const SITE_PATTERNS = {
  close_lead: /app\.close\.com\/lead\/([^\/\?]+)/,
  close_dialer: /app\.close\.com.*dialer/,
  close_smartview: /app\.close\.com.*smart_view/,
  progressive: /foragentsonly\.progressive\.com|progressive\.com\/agent/i,
  geico: /geico\.com/i,
  bhhc: /bfrms\.bhhc\.com|bhhc\.com/i,
  jmwilson: /jmwilson\.com/i,
  fmcsa: /safer\.fmcsa\.dot\.gov/i
};

// State
let currentContext = null;
let lastUrl = window.location.href;
let debounceTimer = null;
let observer = null;

/**
 * Detect which site we're on
 */
function detectSite() {
  const url = window.location.href;

  for (const [site, pattern] of Object.entries(SITE_PATTERNS)) {
    const match = url.match(pattern);
    if (match) {
      return { site, match };
    }
  }

  return { site: 'unknown', match: null };
}

/**
 * Extract context based on current site
 */
function extractContext() {
  const { site, match } = detectSite();
  const url = window.location.href;

  let context = {
    site,
    url,
    timestamp: Date.now()
  };

  switch (site) {
    case 'close_lead':
      context = { ...context, ...extractCloseLeadContext(match) };
      break;
    case 'close_dialer':
      context = { ...context, ...extractCloseDialerContext() };
      break;
    case 'fmcsa':
      context = { ...context, ...extractFMCSAContext() };
      break;
    case 'progressive':
    case 'geico':
    case 'bhhc':
    case 'jmwilson':
      context = { ...context, ...extractCarrierContext(site) };
      break;
    default:
      // Unknown site - just report URL
      context.title = document.title;
      break;
  }

  return context;
}

/**
 * Extract Close CRM lead page context
 */
function extractCloseLeadContext(match) {
  const leadId = match ? match[1] : null;
  const context = { leadId };

  // Company name - try multiple selectors
  const companyEl = document.querySelector('h1[class*="LeadName"]') ||
                    document.querySelector('[data-testid="lead-name"]') ||
                    document.querySelector('.lead-header h1');
  if (companyEl) {
    context.companyName = companyEl.textContent.trim();
  }

  // Contact info
  const contactEl = document.querySelector('[class*="ContactName"]') ||
                    document.querySelector('[data-testid="contact-name"]');
  if (contactEl) {
    context.contactName = contactEl.textContent.trim();
  }

  // Phone
  const phoneEl = document.querySelector('a[href^="tel:"]');
  if (phoneEl) {
    context.phone = phoneEl.textContent.trim();
  }

  // Email
  const emailEl = document.querySelector('a[href^="mailto:"]');
  if (emailEl) {
    context.email = emailEl.textContent.trim();
  }

  // DOT/MC from custom fields or page text
  const pageText = document.body.innerText;

  const dotMatch = pageText.match(/USDOT\s*(?:Number)?[:\s#]*(\d{5,8})/i) ||
                   pageText.match(/DOT[:\s#]+(\d{5,8})/i);
  if (dotMatch) {
    context.dotNumber = dotMatch[1];
  }

  const mcMatch = pageText.match(/MC[:\s#-]*(\d{5,8})/i);
  if (mcMatch) {
    context.mcNumber = mcMatch[1];
  }

  // Lead status
  const statusEl = document.querySelector('[class*="LeadStatus"]') ||
                   document.querySelector('[data-testid="lead-status"]');
  if (statusEl) {
    context.status = statusEl.textContent.trim();
  }

  return context;
}

/**
 * Extract Close CRM dialer context
 */
function extractCloseDialerContext() {
  const context = {};

  // Current call info
  const callerEl = document.querySelector('[class*="dialer"] [class*="name"]') ||
                   document.querySelector('[class*="CallerInfo"]');
  if (callerEl) {
    context.currentCaller = callerEl.textContent.trim();
  }

  // Dialer status
  const statusEl = document.querySelector('[class*="dialer-status"]') ||
                   document.querySelector('[class*="CallStatus"]');
  if (statusEl) {
    context.dialerStatus = statusEl.textContent.trim();
  }

  return context;
}

/**
 * Extract FMCSA SAFER context
 */
function extractFMCSAContext() {
  const context = {};

  // Carrier name - usually in a table or header
  const nameEl = document.querySelector('td:contains("Legal Name")') ||
                 document.evaluate("//td[contains(text(),'Legal Name')]/following-sibling::td",
                   document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;

  // Try to find carrier info from table cells
  const tables = document.querySelectorAll('table');
  tables.forEach(table => {
    const text = table.innerText;

    // DOT Number
    const dotMatch = text.match(/USDOT\s*Number[:\s]*(\d+)/i);
    if (dotMatch) context.dotNumber = dotMatch[1];

    // MC Number
    const mcMatch = text.match(/MC\/MX\/FF\s*Number[:\s]*(\d+)/i);
    if (mcMatch) context.mcNumber = mcMatch[1];

    // Legal Name
    const nameMatch = text.match(/Legal\s*Name[:\s]*([^\n]+)/i);
    if (nameMatch) context.carrierName = nameMatch[1].trim();

    // Operating Status
    const statusMatch = text.match(/Operating\s*Status[:\s]*([^\n]+)/i);
    if (statusMatch) context.operatingStatus = statusMatch[1].trim();
  });

  return context;
}

/**
 * Extract carrier site context (Progressive, Geico, BHHC, JM Wilson)
 */
function extractCarrierContext(site) {
  const context = {
    carrierSite: site,
    pageTitle: document.title
  };

  // Try to detect if we're on a quote or policy page
  const url = window.location.href.toLowerCase();
  const pageText = document.body.innerText.toLowerCase();

  if (url.includes('quote') || pageText.includes('quote')) {
    context.pageType = 'quote';
  } else if (url.includes('policy') || pageText.includes('policy')) {
    context.pageType = 'policy';
  }

  // Try to find DOT number on the page
  const bodyText = document.body.innerText;
  const dotMatch = bodyText.match(/DOT[:\s#]*(\d{5,8})/i) ||
                   bodyText.match(/USDOT[:\s#]*(\d{5,8})/i);
  if (dotMatch) {
    context.dotNumber = dotMatch[1];
  }

  return context;
}

/**
 * Check if context has meaningfully changed
 */
function hasContextChanged(newContext) {
  if (!currentContext) return true;
  if (currentContext.site !== newContext.site) return true;
  if (currentContext.url !== newContext.url) return true;

  // For Close leads, check if key fields changed
  if (newContext.site === 'close_lead') {
    if (currentContext.leadId !== newContext.leadId) return true;
    if (currentContext.companyName !== newContext.companyName) return true;
  }

  return false;
}

/**
 * Send context update to service worker
 */
function sendContextUpdate(context, force = false) {
  if (!force && !hasContextChanged(context)) {
    return;
  }

  // Track what changed
  const changed = [];
  if (currentContext) {
    for (const key of Object.keys(context)) {
      if (context[key] !== currentContext[key]) {
        changed.push(key);
      }
    }
  }

  const message = {
    type: 'PAGE_CONTEXT_UPDATE',
    ...context,
    changed: changed.length > 0 ? changed : undefined
  };

  console.log('[PageWatcher] Context update:', message);

  chrome.runtime.sendMessage(message).catch(err => {
    // Extension context may be invalidated, ignore
  });

  currentContext = context;
}

/**
 * Debounced context check - prevents spam during rapid DOM changes
 */
function debouncedContextCheck() {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }

  debounceTimer = setTimeout(() => {
    const context = extractContext();
    sendContextUpdate(context);
  }, 150); // 150ms debounce
}

/**
 * Handle URL changes (SPA navigation)
 */
function checkUrlChange() {
  const currentUrl = window.location.href;
  if (currentUrl !== lastUrl) {
    lastUrl = currentUrl;
    console.log('[PageWatcher] URL changed:', currentUrl);
    debouncedContextCheck();
  }
}

/**
 * Start watching the page
 */
function startWatching() {
  console.log('[PageWatcher] Starting page watcher');

  // Initial context extraction
  const context = extractContext();
  sendContextUpdate(context, true);

  // Watch for URL changes (SPA navigation)
  // Use both popstate and a polling check for pushState
  window.addEventListener('popstate', checkUrlChange);
  setInterval(checkUrlChange, 500); // Check every 500ms for pushState changes

  // Watch for DOM mutations
  observer = new MutationObserver((mutations) => {
    // Filter out trivial mutations
    const significantMutation = mutations.some(mutation => {
      // Ignore text-only changes in non-significant elements
      if (mutation.type === 'characterData') {
        return false;
      }

      // Check if mutation is in a significant area
      const target = mutation.target;
      if (target.nodeType === Node.ELEMENT_NODE) {
        const tag = target.tagName.toLowerCase();
        // Ignore script, style, and meta changes
        if (['script', 'style', 'meta', 'link'].includes(tag)) {
          return false;
        }
        // Look for changes in main content areas
        if (target.closest('main, article, [role="main"], .lead-header, .lead-content')) {
          return true;
        }
      }

      // Added/removed nodes
      if (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0) {
        return true;
      }

      return false;
    });

    if (significantMutation) {
      debouncedContextCheck();
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class', 'data-testid']
  });

  console.log('[PageWatcher] Watching started for site:', context.site);
}

/**
 * Stop watching
 */
function stopWatching() {
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }
}

// Listen for manual refresh requests
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_PAGE_CONTEXT') {
    const context = extractContext();
    sendResponse({ success: true, context });
    return true;
  }

  if (message.type === 'REFRESH_CONTEXT') {
    const context = extractContext();
    sendContextUpdate(context, true);
    sendResponse({ success: true });
    return true;
  }
});

// Start watching when script loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startWatching);
} else {
  startWatching();
}

// Cleanup on unload
window.addEventListener('unload', stopWatching);
