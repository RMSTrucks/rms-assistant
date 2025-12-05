/**
 * RMS Work Assistant - Browser Tools Content Script
 *
 * Injected into all pages to provide:
 * - DOM element interaction (click, fill, select)
 * - Page state extraction
 * - Element targeting by various strategies
 */

console.log('[RMS Browser Tools] Content script loaded');

// ============================================================================
// ELEMENT TARGETING
// ============================================================================

/**
 * Find element using multiple strategies
 * Priority: id > name > selector > xpath > label text
 */
function findElement(target) {
  // If it's already a selector, try it directly
  if (target.selector) {
    return document.querySelector(target.selector);
  }

  // Try by ID
  if (target.id) {
    const el = document.getElementById(target.id);
    if (el) return el;
  }

  // Try by name attribute
  if (target.name) {
    const el = document.querySelector(`[name="${target.name}"]`);
    if (el) return el;
  }

  // Try by fieldref (for ExtJS)
  if (target.fieldref) {
    const el = document.querySelector(`[fieldref="${target.fieldref}"]`);
    if (el) return el;
  }

  // Try by label text
  if (target.label) {
    const el = findByLabel(target.label);
    if (el) return el;
  }

  // Try by placeholder
  if (target.placeholder) {
    const el = document.querySelector(`[placeholder*="${target.placeholder}" i]`);
    if (el) return el;
  }

  // Try by button text
  if (target.buttonText) {
    const buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"]');
    for (const btn of buttons) {
      if (btn.textContent?.toLowerCase().includes(target.buttonText.toLowerCase()) ||
          btn.value?.toLowerCase().includes(target.buttonText.toLowerCase())) {
        return btn;
      }
    }
  }

  return null;
}

/**
 * Find input by its associated label text
 */
function findByLabel(labelText) {
  const searchText = labelText.toLowerCase();

  // Try label elements with for attribute
  const labels = document.querySelectorAll('label');
  for (const label of labels) {
    if (label.textContent?.toLowerCase().includes(searchText)) {
      if (label.htmlFor) {
        const input = document.getElementById(label.htmlFor);
        if (input) return input;
      }
      // Check for nested input
      const nestedInput = label.querySelector('input, select, textarea');
      if (nestedInput) return nestedInput;
    }
  }

  // XPath approach for adjacent labels
  const xpathSearchText = searchText.includes("'")
    ? `concat('${searchText.replace(/'/g, "',\"'\",'")}')`.toLowerCase()
    : `'${searchText}'`;

  try {
    const xpath = `//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), ${xpathSearchText})]/following::input[1]`;
    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
    if (result.singleNodeValue) return result.singleNodeValue;
  } catch (e) {
    // XPath failed, continue with other methods
  }

  return null;
}

// ============================================================================
// ELEMENT INTERACTION
// ============================================================================

/**
 * Fill a form field with value
 * Handles ExtJS and React frameworks properly
 */
function fillField(target, value) {
  const el = findElement(target);
  if (!el) {
    return { success: false, error: 'Element not found', target };
  }

  try {
    // Focus the element
    el.focus();

    // Use native value setter (works with React, ExtJS, etc.)
    const prototype = el.tagName === 'TEXTAREA'
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;

    const nativeSetter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;

    if (nativeSetter) {
      nativeSetter.call(el, value);
    } else {
      el.value = value;
    }

    // Dispatch events in the right order
    el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
    el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
    el.dispatchEvent(new Event('blur', { bubbles: true, cancelable: true }));

    return { success: true, element: describeElement(el) };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Click an element
 */
function clickElement(target) {
  const el = findElement(target);
  if (!el) {
    return { success: false, error: 'Element not found', target };
  }

  try {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.click();
    return { success: true, element: describeElement(el) };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Select an option in a dropdown
 */
function selectOption(target, optionValue) {
  const el = findElement(target);
  if (!el || el.tagName !== 'SELECT') {
    return { success: false, error: 'Select element not found', target };
  }

  try {
    // Find option by value or text
    let option = el.querySelector(`option[value="${optionValue}"]`);
    if (!option) {
      // Try by text content
      option = Array.from(el.options).find(opt =>
        opt.textContent?.toLowerCase().includes(optionValue.toLowerCase())
      );
    }

    if (option) {
      el.value = option.value;
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return { success: true, element: describeElement(el), selected: option.textContent };
    }

    return { success: false, error: 'Option not found', optionValue };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Click a radio button
 */
function selectRadio(target, value) {
  // Find by label text containing target
  const searchText = target.label?.toLowerCase() || target.toLowerCase();

  // Find all radio buttons
  const radios = document.querySelectorAll('input[type="radio"]');

  for (const radio of radios) {
    // Check label
    const label = document.querySelector(`label[for="${radio.id}"]`);
    const labelText = label?.textContent?.toLowerCase() || '';

    // Check parent text
    const parentText = radio.parentElement?.textContent?.toLowerCase() || '';

    if (labelText.includes(searchText) || parentText.includes(searchText)) {
      // Found the group, now find yes/no
      const name = radio.name;
      const groupRadios = document.querySelectorAll(`input[name="${name}"]`);

      for (const r of groupRadios) {
        const rLabel = document.querySelector(`label[for="${r.id}"]`)?.textContent?.toLowerCase() || '';
        const rParent = r.parentElement?.textContent?.toLowerCase() || '';

        const isYes = value === true || value === 'yes' || value === 'true';
        const matchesYes = rLabel.includes('yes') || rParent.includes('yes');
        const matchesNo = rLabel.includes('no') || rParent.includes('no');

        if ((isYes && matchesYes) || (!isYes && matchesNo)) {
          r.click();
          r.dispatchEvent(new Event('change', { bubbles: true }));
          return { success: true, selected: isYes ? 'Yes' : 'No' };
        }
      }
    }
  }

  return { success: false, error: 'Radio button not found', target };
}

// ============================================================================
// PAGE STATE EXTRACTION
// ============================================================================

/**
 * Get current page state for agent context
 */
function getPageState() {
  return {
    url: window.location.href,
    title: document.title,
    forms: extractForms(),
    buttons: extractButtons(),
    links: extractLinks().slice(0, 20),
    text: extractMainText()
  };
}

function extractForms() {
  const forms = [];
  const inputs = document.querySelectorAll('input, select, textarea');

  inputs.forEach((el, index) => {
    if (index > 100) return;  // Limit

    const label = findLabelFor(el);
    forms.push({
      tag: el.tagName.toLowerCase(),
      type: el.type,
      name: el.name,
      id: el.id,
      label: label,
      value: el.type === 'password' ? '***' : el.value?.substring(0, 50),
      placeholder: el.placeholder,
      required: el.required,
      disabled: el.disabled
    });
  });

  return forms;
}

function extractButtons() {
  const buttons = [];
  const els = document.querySelectorAll('button, input[type="button"], input[type="submit"], [role="button"]');

  els.forEach((el, index) => {
    if (index > 30) return;

    buttons.push({
      text: el.textContent?.trim().substring(0, 50) || el.value,
      id: el.id,
      disabled: el.disabled
    });
  });

  return buttons;
}

function extractLinks() {
  const links = [];
  document.querySelectorAll('a[href]').forEach((a, index) => {
    if (index > 20) return;
    links.push({
      text: a.textContent?.trim().substring(0, 50),
      href: a.href
    });
  });
  return links;
}

function extractMainText() {
  // Get main content text (simplified)
  const main = document.querySelector('main, article, [role="main"]') || document.body;
  return main.textContent?.replace(/\s+/g, ' ').trim().substring(0, 1000);
}

function findLabelFor(el) {
  // Check for label with for attribute
  if (el.id) {
    const label = document.querySelector(`label[for="${el.id}"]`);
    if (label) return label.textContent?.trim();
  }

  // Check parent label
  const parent = el.closest('label');
  if (parent) return parent.textContent?.trim();

  // Check previous sibling
  const prev = el.previousElementSibling;
  if (prev?.tagName === 'LABEL') return prev.textContent?.trim();

  return null;
}

function describeElement(el) {
  return {
    tag: el.tagName.toLowerCase(),
    id: el.id,
    name: el.name,
    text: el.textContent?.substring(0, 50)
  };
}

// ============================================================================
// CLOSE CRM DATA EXTRACTION
// ============================================================================

/**
 * Extract lead data from Close CRM page for quote form pre-fill
 */
function extractLeadDataFromPage() {
  // Only works on Close CRM
  if (!window.location.href.includes('app.close.com/lead/')) {
    return { success: false, error: 'Not on a Close CRM lead page' };
  }

  const data = {};

  try {
    // Company name - from header
    const companyNameEl = document.querySelector('h1[class*="LeadName"]') ||
                          document.querySelector('[data-testid="lead-name"]') ||
                          document.querySelector('.lead-name') ||
                          document.querySelector('h1');
    if (companyNameEl) {
      data.companyName = companyNameEl.textContent?.trim();
    }

    // Address - from ABOUT section
    const aboutSection = document.querySelector('[class*="About"]') ||
                         document.querySelector('[data-section="about"]');
    if (aboutSection) {
      // Look for address icon (location pin)
      const addressEl = aboutSection.querySelector('[class*="address"]') ||
                        aboutSection.querySelector('svg[data-icon="map-marker-alt"]')?.parentElement?.parentElement;
      if (addressEl) {
        const addressText = addressEl.textContent?.trim();
        if (addressText) {
          // Try to parse address
          const parts = addressText.split('\n').map(s => s.trim()).filter(Boolean);
          if (parts.length >= 1) data.address = parts[0];
          // Try to parse city, state, zip from second line
          if (parts.length >= 2) {
            const cityStateZip = parts[1];
            const match = cityStateZip.match(/^(.+),\s*([A-Z]{2})\s*(\d{5})?/);
            if (match) {
              data.city = match[1];
              data.state = match[2];
              data.zip = match[3];
            }
          }
        }
      }
    }

    // Phone - from Contacts section
    const phoneEl = document.querySelector('a[href^="tel:"]');
    if (phoneEl) {
      data.phone = phoneEl.textContent?.trim() || phoneEl.getAttribute('href')?.replace('tel:', '');
    }

    // Email - from Contacts section
    const emailEl = document.querySelector('a[href^="mailto:"]');
    if (emailEl) {
      data.email = emailEl.textContent?.trim() || emailEl.getAttribute('href')?.replace('mailto:', '');
    }

    // Contact name - first contact in list
    const contactSection = document.querySelector('[class*="Contacts"]') ||
                           document.querySelector('[data-section="contacts"]');
    if (contactSection) {
      const contactNameEl = contactSection.querySelector('[class*="ContactName"]') ||
                            contactSection.querySelector('a[href*="/contact/"]');
      if (contactNameEl) {
        data.contactName = contactNameEl.textContent?.trim();
      }
    }

    // DOT Number - from Custom Fields
    const customFieldsSection = document.querySelector('[class*="CustomFields"]') ||
                                document.querySelector('[data-section="custom-fields"]');

    // Look for USDOT field
    const allText = document.body.innerText;

    // Try to find DOT number pattern
    const dotMatch = allText.match(/USDOT\s*(?:Number)?[:\s]*(\d{5,8})/i) ||
                     allText.match(/DOT\s*#?[:\s]*(\d{5,8})/i);
    if (dotMatch) {
      data.dotNumber = dotMatch[1];
    }

    // Try to find MC number
    const mcMatch = allText.match(/MC\s*#?[:\s]*(\d{5,8})/i);
    if (mcMatch) {
      data.mcNumber = mcMatch[1];
    }

    console.log('[RMS Browser Tools] Extracted lead data:', data);
    return { success: true, data };

  } catch (error) {
    console.error('[RMS Browser Tools] Error extracting lead data:', error);
    return { success: false, error: error.message };
  }
}

// ============================================================================
// MESSAGE HANDLING
// ============================================================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[RMS Browser Tools] Message received:', message);

  switch (message.type) {
    case 'FILL_FIELD':
      sendResponse(fillField(message.target, message.value));
      break;

    case 'CLICK_ELEMENT':
      sendResponse(clickElement(message.target));
      break;

    case 'SELECT_OPTION':
      sendResponse(selectOption(message.target, message.value));
      break;

    case 'SELECT_RADIO':
      sendResponse(selectRadio(message.target, message.value));
      break;

    case 'GET_PAGE_STATE':
      sendResponse({ success: true, pageState: getPageState() });
      break;

    case 'FIND_ELEMENT':
      const el = findElement(message.target);
      sendResponse({
        success: !!el,
        element: el ? describeElement(el) : null
      });
      break;

    case 'GET_LEAD_DATA':
      // Extract lead data from Close CRM page
      sendResponse(extractLeadDataFromPage());
      break;

    default:
      sendResponse({ success: false, error: 'Unknown message type' });
  }

  return true;  // Keep channel open for async
});
