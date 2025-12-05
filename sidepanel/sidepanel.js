/**
 * RMS Work Assistant - Side Panel Chat Interface
 *
 * Handles:
 * - Message display and history
 * - WebSocket connection to agent server
 * - Streaming response display
 * - Action confirmation dialogs
 * - Tab state tracking
 */

// Configuration
const CONFIG = {
  wsUrl: 'ws://localhost:8765/ws',  // Agent server WebSocket endpoint
  reconnectDelay: 3000,
  maxReconnectAttempts: 5,
  messageHistoryKey: 'rms_assistant_messages'
};

// Tool display names and icons
const TOOL_DISPLAY = {
  // Close CRM
  'search_leads': { name: 'Close CRM Search', icon: '🔍', loadingText: 'Searching Close CRM...' },
  'get_lead': { name: 'Close CRM Lookup', icon: '📋', loadingText: 'Fetching lead details...' },
  'get_lead_activities': { name: 'Close CRM Activities', icon: '📊', loadingText: 'Loading activities...' },
  // NowCerts
  'search_insured': { name: 'NowCerts Search', icon: '🏢', loadingText: 'Searching NowCerts...' },
  'get_insured': { name: 'NowCerts Lookup', icon: '📄', loadingText: 'Fetching insured details...' },
  'get_policies': { name: 'NowCerts Policies', icon: '📑', loadingText: 'Loading policies...' },
  'get_certificates': { name: 'NowCerts Certificates', icon: '📜', loadingText: 'Loading certificates...' },
  // FMCSA/DOT
  'get_dot_info': { name: 'FMCSA DOT Lookup', icon: '🚛', loadingText: 'Looking up DOT number...' },
  'search_by_name': { name: 'FMCSA Name Search', icon: '🔎', loadingText: 'Searching FMCSA...' },
  // Browser
  'navigate': { name: 'Navigate', icon: '🌐', loadingText: 'Navigating...' },
  'click': { name: 'Click Element', icon: '👆', loadingText: 'Clicking...' },
  'fill_form': { name: 'Fill Form', icon: '📝', loadingText: 'Filling form...' },
  'screenshot': { name: 'Screenshot', icon: '📸', loadingText: 'Taking screenshot...' },
  // Default
  'default': { name: 'Tool', icon: '⚙️', loadingText: 'Working...' }
};

// State
const state = {
  ws: null,
  connected: false,
  reconnectAttempts: 0,
  messages: [],
  currentTab: null,
  pendingAction: null,
  isStreaming: false,
  pendingFiles: []  // Files to attach to next message
};

// DOM Elements
const elements = {
  connectionStatus: document.getElementById('connectionStatus'),
  messagesContainer: document.getElementById('messagesContainer'),
  messageInput: document.getElementById('messageInput'),
  sendButton: document.getElementById('sendButton'),
  tabInfo: document.getElementById('tabInfo'),
  actionOverlay: document.getElementById('actionOverlay'),
  actionBody: document.getElementById('actionBody'),
  actionAllow: document.getElementById('actionAllow'),
  actionDeny: document.getElementById('actionDeny'),
  quickActions: document.getElementById('quickActions'),
  dropZone: document.getElementById('dropZone'),
  dropOverlay: document.getElementById('dropOverlay'),
  attachButton: document.getElementById('attachButton'),
  fileInput: document.getElementById('fileInput'),
  filePreview: document.getElementById('filePreview')
};

// ============================================================================
// MESSAGE DISPLAY
// ============================================================================

function addMessage(role, content, options = {}) {
  const message = { role, content, timestamp: Date.now(), ...options };
  state.messages.push(message);
  renderMessage(message);
  saveMessages();
  scrollToBottom();
}

function renderMessage(message) {
  // Remove welcome message on first real message
  const welcome = elements.messagesContainer.querySelector('.welcome-message');
  if (welcome && state.messages.length > 0) {
    welcome.remove();
  }

  const div = document.createElement('div');

  if (message.type === 'tool') {
    div.className = 'tool-card';
    div.id = message.toolId || '';
    const toolInfo = TOOL_DISPLAY[message.toolKey] || TOOL_DISPLAY['default'];

    if (message.toolStatus === 'complete') {
      div.classList.add('complete');
      div.innerHTML = `
        <div class="tool-icon success">✓</div>
        <div class="tool-content">
          <div class="tool-name">${toolInfo.name}</div>
          <div class="tool-summary">${escapeHtml(message.toolSummary || 'Done')}</div>
        </div>
      `;
    } else if (message.toolStatus === 'error') {
      div.classList.add('error');
      div.innerHTML = `
        <div class="tool-icon error">✕</div>
        <div class="tool-content">
          <div class="tool-name">${toolInfo.name}</div>
          <div class="tool-summary">${escapeHtml(message.toolSummary || 'Error')}</div>
        </div>
      `;
    } else {
      div.classList.add('loading');
      div.innerHTML = `
        <div class="tool-icon">${toolInfo.icon}</div>
        <div class="tool-content">
          <div class="tool-name">${toolInfo.loadingText}</div>
          <div class="tool-spinner"></div>
        </div>
      `;
    }
  } else {
    div.className = `message ${message.role}`;
    if (message.streaming) {
      div.classList.add('streaming');
    }
    div.innerHTML = formatMessage(message.content);
    div.id = message.id || '';
  }

  elements.messagesContainer.appendChild(div);
}

function updateStreamingMessage(id, content) {
  const div = document.getElementById(id);
  if (div) {
    div.innerHTML = formatMessage(content);
  }
}

function finishStreamingMessage(id) {
  const div = document.getElementById(id);
  if (div) {
    div.classList.remove('streaming');
  }
  state.isStreaming = false;
}

function showThinkingIndicator() {
  const div = document.createElement('div');
  div.className = 'thinking-indicator';
  div.id = 'thinking';
  div.innerHTML = `
    <div class="thinking-dots">
      <span></span>
      <span></span>
      <span></span>
    </div>
    <span>Thinking...</span>
  `;
  elements.messagesContainer.appendChild(div);
  scrollToBottom();
}

function hideThinkingIndicator() {
  const thinking = document.getElementById('thinking');
  if (thinking) {
    thinking.remove();
  }
}

function formatMessage(content) {
  // Basic markdown-like formatting
  let html = escapeHtml(content);

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Code blocks
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Line breaks
  html = html.replace(/\n/g, '<br>');

  return html;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function summarizeToolResult(toolKey, result) {
  // Generate human-readable summary from tool results
  if (!result) return 'No results';

  if (typeof result === 'string') {
    // Truncate long strings
    if (result.startsWith('Error')) return result.substring(0, 100);
    if (result.length > 80) return result.substring(0, 77) + '...';
    return result;
  }

  // Handle specific tool results
  switch (toolKey) {
    case 'search_leads':
      if (result.leads) return `Found ${result.leads.length} lead${result.leads.length !== 1 ? 's' : ''}`;
      if (Array.isArray(result)) return `Found ${result.length} lead${result.length !== 1 ? 's' : ''}`;
      break;
    case 'get_lead':
      if (result.name || result.display_name) return `Loaded: ${result.name || result.display_name}`;
      break;
    case 'search_insured':
      if (result.value) return `Found ${result.value.length} insured${result.value.length !== 1 ? 's' : ''}`;
      if (Array.isArray(result)) return `Found ${result.length} insured${result.length !== 1 ? 's' : ''}`;
      break;
    case 'get_dot_info':
      if (result.carrier) return `Found: ${result.carrier.legalName || result.carrier.dbaName || 'Carrier'}`;
      if (result.legalName) return `Found: ${result.legalName}`;
      break;
    case 'get_policies':
      if (Array.isArray(result)) return `Found ${result.length} polic${result.length !== 1 ? 'ies' : 'y'}`;
      break;
    case 'navigate':
      return 'Navigation complete';
    case 'click':
      return 'Click complete';
    case 'fill_form':
      return 'Form filled';
    case 'screenshot':
      return 'Screenshot captured';
  }

  // Default: show type and count if object/array
  if (Array.isArray(result)) return `Returned ${result.length} item${result.length !== 1 ? 's' : ''}`;
  if (typeof result === 'object') return 'Data retrieved';

  return 'Done';
}

function scrollToBottom() {
  elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
}

// ============================================================================
// DATA PREVIEW CARDS
// ============================================================================

function renderDataCard(dataType, data) {
  const div = document.createElement('div');
  div.className = `data-card ${dataType}-card`;

  switch (dataType) {
    case 'lead':
      div.innerHTML = renderLeadCard(data);
      break;
    case 'policy':
      div.innerHTML = renderPolicyCard(data);
      break;
    case 'dot':
      div.innerHTML = renderDOTCard(data);
      break;
    case 'insured':
      div.innerHTML = renderInsuredCard(data);
      break;
    default:
      div.innerHTML = `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
  }

  elements.messagesContainer.appendChild(div);
  scrollToBottom();

  // Add click handlers for card actions
  div.querySelectorAll('.card-action').forEach(btn => {
    btn.addEventListener('click', handleCardAction);
  });
}

function renderLeadCard(lead) {
  const status = lead.status || lead.status_label || 'Unknown';
  const statusClass = status.toLowerCase().replace(/\s+/g, '-');
  const contactName = lead.contact?.name || lead.contacts?.[0]?.name || '';
  const phone = lead.contact?.phone || lead.contacts?.[0]?.phones?.[0]?.phone || '';

  return `
    <div class="card-header">
      <span class="card-type-badge">Lead</span>
      <span class="card-status ${statusClass}">${escapeHtml(status)}</span>
    </div>
    <div class="card-title">${escapeHtml(lead.name || lead.display_name || 'Unknown')}</div>
    ${contactName ? `<div class="card-contact">${escapeHtml(contactName)}</div>` : ''}
    ${phone ? `<a href="tel:${phone}" class="card-phone">${escapeHtml(phone)}</a>` : ''}
    <div class="card-actions">
      <button class="card-action" data-action="view-lead" data-id="${lead.id}">View in Close</button>
      ${phone ? `<button class="card-action primary" data-action="call" data-phone="${phone}">Call</button>` : ''}
    </div>
  `;
}

function renderPolicyCard(policy) {
  const expDate = policy.expirationDate || policy.expiration_date || '';
  const formattedExp = expDate ? new Date(expDate).toLocaleDateString() : 'N/A';

  return `
    <div class="card-header">
      <span class="card-type-badge policy">Policy</span>
      <span class="card-status">${escapeHtml(policy.status || 'Active')}</span>
    </div>
    <div class="card-title">${escapeHtml(policy.policyNumber || policy.policy_number || 'N/A')}</div>
    <div class="card-detail">
      <span class="label">Carrier:</span>
      <span class="value">${escapeHtml(policy.carrier || policy.carrierName || 'N/A')}</span>
    </div>
    <div class="card-detail">
      <span class="label">Expires:</span>
      <span class="value">${formattedExp}</span>
    </div>
    ${policy.limits ? `<div class="card-detail"><span class="label">Limits:</span><span class="value">${escapeHtml(policy.limits)}</span></div>` : ''}
  `;
}

function renderDOTCard(dot) {
  const carrier = dot.carrier || dot;
  const name = carrier.legalName || carrier.dbaName || carrier.name || 'Unknown';
  const rating = carrier.safetyRating || carrier.safety_rating || 'Not Rated';

  return `
    <div class="card-header">
      <span class="card-type-badge dot">DOT</span>
      <span class="card-status">${escapeHtml(rating)}</span>
    </div>
    <div class="card-title">${escapeHtml(name)}</div>
    <div class="card-detail">
      <span class="label">DOT #:</span>
      <span class="value">${escapeHtml(carrier.dotNumber || carrier.dot_number || 'N/A')}</span>
    </div>
    ${carrier.totalDrivers ? `<div class="card-detail"><span class="label">Drivers:</span><span class="value">${carrier.totalDrivers}</span></div>` : ''}
    ${carrier.totalPowerUnits ? `<div class="card-detail"><span class="label">Power Units:</span><span class="value">${carrier.totalPowerUnits}</span></div>` : ''}
  `;
}

function renderInsuredCard(insured) {
  return `
    <div class="card-header">
      <span class="card-type-badge insured">Insured</span>
    </div>
    <div class="card-title">${escapeHtml(insured.commercialName || insured.name || 'Unknown')}</div>
    ${insured.phone ? `<a href="tel:${insured.phone}" class="card-phone">${escapeHtml(insured.phone)}</a>` : ''}
    ${insured.email ? `<div class="card-detail"><span class="label">Email:</span><span class="value">${escapeHtml(insured.email)}</span></div>` : ''}
    <div class="card-actions">
      <button class="card-action" data-action="view-insured" data-id="${insured.id || insured.insuredId}">View in NowCerts</button>
    </div>
  `;
}

function handleCardAction(e) {
  const action = e.target.dataset.action;
  const id = e.target.dataset.id;
  const phone = e.target.dataset.phone;

  switch (action) {
    case 'view-lead':
      // Open lead in Close CRM
      window.open(`https://app.close.com/lead/${id}/`, '_blank');
      break;
    case 'view-insured':
      // Would need NowCerts URL pattern
      elements.messageInput.value = `Show me details for insured ${id}`;
      elements.messageInput.focus();
      break;
    case 'call':
      window.open(`tel:${phone}`, '_self');
      break;
  }
}

// ============================================================================
// TASK SUGGESTIONS
// ============================================================================

function renderTaskSuggestion(task) {
  const div = document.createElement('div');
  div.className = 'task-suggestion';
  div.id = `task-${task.taskId}`;
  div.innerHTML = `
    <div class="task-icon">📋</div>
    <div class="task-content">
      <div class="task-text">${escapeHtml(task.description)}</div>
      ${task.dueDate ? `<div class="task-due">Due: ${escapeHtml(task.dueDate)}</div>` : ''}
    </div>
    <button class="task-create-btn" data-task-id="${task.taskId}" data-lead-id="${task.leadId || ''}">
      Create Task
    </button>
  `;

  elements.messagesContainer.appendChild(div);
  scrollToBottom();

  // Add click handler
  div.querySelector('.task-create-btn').addEventListener('click', handleCreateTask);
}

function handleCreateTask(e) {
  const taskId = e.target.dataset.taskId;
  const leadId = e.target.dataset.leadId;

  // Disable button and show loading
  e.target.disabled = true;
  e.target.textContent = 'Creating...';

  // Send create task request to server
  if (state.ws && state.connected) {
    state.ws.send(JSON.stringify({
      type: 'create_task',
      taskId: taskId,
      leadId: leadId
    }));
  }
}

function updateTaskConfirmation(taskId, taskDetails) {
  const taskDiv = document.getElementById(`task-${taskId}`);
  if (taskDiv) {
    taskDiv.classList.add('created');
    const btn = taskDiv.querySelector('.task-create-btn');
    if (btn) {
      btn.textContent = '✓ Created';
      btn.classList.add('success');
    }
  }
}

// ============================================================================
// MESSAGE PERSISTENCE
// ============================================================================

function saveMessages() {
  // Keep last 100 messages
  const toSave = state.messages.slice(-100);
  chrome.storage.local.set({ [CONFIG.messageHistoryKey]: toSave });
}

async function loadMessages() {
  const result = await chrome.storage.local.get(CONFIG.messageHistoryKey);
  const messages = result[CONFIG.messageHistoryKey] || [];

  if (messages.length > 0) {
    // Clear welcome message
    const welcome = elements.messagesContainer.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // Render saved messages
    messages.forEach(msg => {
      state.messages.push(msg);
      renderMessage(msg);
    });
    scrollToBottom();
  }
}

// ============================================================================
// WEBSOCKET CONNECTION
// ============================================================================

function connectWebSocket() {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    return;
  }

  console.log('[RMS Assistant] Connecting to agent server...');
  state.ws = new WebSocket(CONFIG.wsUrl);

  state.ws.onopen = () => {
    console.log('[RMS Assistant] Connected to agent server');
    state.connected = true;
    state.reconnectAttempts = 0;
    updateConnectionStatus(true);

    // Send current tab state
    sendTabState();
  };

  state.ws.onclose = () => {
    console.log('[RMS Assistant] Disconnected from agent server');
    state.connected = false;
    updateConnectionStatus(false);

    // Attempt reconnect
    if (state.reconnectAttempts < CONFIG.maxReconnectAttempts) {
      state.reconnectAttempts++;
      setTimeout(connectWebSocket, CONFIG.reconnectDelay);
    }
  };

  state.ws.onerror = () => {
    console.error('[RMS Assistant] WebSocket connection error (server may be down)');
  };

  state.ws.onmessage = (event) => {
    handleServerMessage(JSON.parse(event.data));
  };
}

function updateConnectionStatus(connected) {
  elements.connectionStatus.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
  elements.connectionStatus.querySelector('.status-text').textContent = connected ? 'Connected' : 'Disconnected';
}

// ============================================================================
// MESSAGE HANDLING
// ============================================================================

function handleServerMessage(data) {
  console.log('[RMS Assistant] Server message:', data);

  switch (data.type) {
    case 'response_start':
      hideThinkingIndicator();
      state.isStreaming = true;
      const streamId = 'stream-' + Date.now();
      const streamMsg = {
        role: 'assistant',
        content: '',
        id: streamId,
        streaming: true,
        timestamp: Date.now()
      };
      state.messages.push(streamMsg);
      renderMessage(streamMsg);
      state.currentStreamId = streamId;
      break;

    case 'response_chunk':
      if (state.currentStreamId) {
        const msg = state.messages.find(m => m.id === state.currentStreamId);
        if (msg) {
          msg.content += data.content;
          updateStreamingMessage(state.currentStreamId, msg.content);
          scrollToBottom();
        }
      }
      break;

    case 'response_end':
      if (state.currentStreamId) {
        finishStreamingMessage(state.currentStreamId);
        state.currentStreamId = null;
        saveMessages();
      }
      break;

    case 'tool_call':
      const toolId = 'tool-' + Date.now();
      addMessage('assistant', '', {
        type: 'tool',
        toolId: toolId,
        toolKey: data.tool,
        toolStatus: 'loading',
        toolArgs: data.args
      });
      state.currentToolId = toolId;
      break;

    case 'tool_result':
      // Update the tool card with result
      if (state.currentToolId) {
        const toolCard = document.getElementById(state.currentToolId);
        const toolMsg = state.messages.find(m => m.toolId === state.currentToolId);

        if (toolCard && toolMsg) {
          const toolInfo = TOOL_DISPLAY[toolMsg.toolKey] || TOOL_DISPLAY['default'];
          const summary = summarizeToolResult(toolMsg.toolKey, data.result);
          const isError = data.result && (data.result.error || (typeof data.result === 'string' && data.result.startsWith('Error')));

          toolMsg.toolStatus = isError ? 'error' : 'complete';
          toolMsg.toolSummary = summary;

          toolCard.className = `tool-card ${isError ? 'error' : 'complete'}`;
          toolCard.innerHTML = `
            <div class="tool-icon ${isError ? 'error' : 'success'}">${isError ? '✕' : '✓'}</div>
            <div class="tool-content">
              <div class="tool-name">${toolInfo.name}</div>
              <div class="tool-summary">${escapeHtml(summary)}</div>
            </div>
          `;
        }
        state.currentToolId = null;
      }
      break;

    case 'action_request':
      showActionConfirmation(data);
      break;

    case 'error':
      hideThinkingIndicator();
      addMessage('assistant', `Error: ${data.message}`);
      break;

    case 'structured_data':
      // Render data as visual card (lead, policy, DOT info)
      renderDataCard(data.dataType, data.data);
      break;

    case 'suggested_task':
      // Show task creation suggestion
      renderTaskSuggestion(data);
      break;

    case 'task_created':
      // Update task suggestion to show confirmation
      updateTaskConfirmation(data.taskId, data.taskDetails);
      break;

    case 'browser_action':
      // Forward browser actions to service worker for execution
      console.log('[RMS Assistant] Forwarding browser action to service worker:', data);
      chrome.runtime.sendMessage({
        type: 'EXECUTE_BROWSER_ACTION',
        action: data
      }, (response) => {
        // Send result back to Python server
        console.log('[RMS Assistant] Browser action result:', response);
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
          state.ws.send(JSON.stringify({
            type: 'browser_action_result',
            actionId: data.actionId,
            result: response || { error: 'No response from service worker' }
          }));
        }
      });
      break;

    case 'agent_message':
      // Show a message from the automation agent in the chat
      hideThinkingIndicator();
      addMessage('assistant', data.message);
      saveMessages();
      break;

    case 'carrier_quote_progress':
      // Show progress update for carrier quote automation
      console.log(`[RMS Assistant] ${data.carrier} quote progress: ${data.status}`);
      // Update status in UI (could show as a subtle notification)
      updateCarrierQuoteStatus(data.carrier, data.status, data.tabId);
      break;
  }
}

function updateCarrierQuoteStatus(carrier, status, tabId) {
  // Show carrier quote progress in a subtle way
  // For now, just log it - can enhance with a progress indicator later
  const statusLine = document.getElementById('carrier-status');
  if (statusLine) {
    statusLine.textContent = `${carrier}: ${status}`;
    statusLine.style.display = 'block';
  } else {
    // Create status element if it doesn't exist
    const statusEl = document.createElement('div');
    statusEl.id = 'carrier-status';
    statusEl.className = 'carrier-status';
    statusEl.textContent = `${carrier}: ${status}`;
    // Insert before chat container
    const chatContainer = elements.chatContainer;
    if (chatContainer) {
      chatContainer.parentNode.insertBefore(statusEl, chatContainer);
    }
  }
}

async function sendMessage(content) {
  const hasFiles = state.pendingFiles.length > 0;
  if (!content.trim() && !hasFiles) return;

  // Build display message
  let displayContent = content;
  if (hasFiles) {
    const fileNames = state.pendingFiles.map(f => f.name).join(', ');
    displayContent = content ? `${content}\n[Attached: ${fileNames}]` : `[Attached: ${fileNames}]`;
  }

  // Add user message to display
  addMessage('user', displayContent);

  // Capture files before clearing
  const filesToSend = [...state.pendingFiles];

  // Clear input and files
  elements.messageInput.value = '';
  clearPendingFiles();
  autoResizeTextarea();
  updateSendButton();

  // Show thinking indicator
  showThinkingIndicator();

  if (state.connected && state.ws) {
    // Send to agent server with files
    const payload = {
      type: 'message',
      content: content || 'Please analyze this file.',
      tabState: state.currentTab
    };

    if (filesToSend.length > 0) {
      payload.files = filesToSend;
    }

    state.ws.send(JSON.stringify(payload));
  } else {
    // Mock response for testing without server
    setTimeout(() => {
      hideThinkingIndicator();
      mockStreamResponse(content);
    }, 500);
  }
}

// ============================================================================
// MOCK RESPONSES (for testing without server)
// ============================================================================

function mockStreamResponse(userMessage) {
  const responses = [
    "I understand you want to work on that. Let me help you get started.",
    "I can help with that! First, let me check the current page state.",
    "Sure thing. I'll look into that for you.",
    "Let me search for that information in Close CRM.",
    "I'm ready to help. What specific details do you need?"
  ];

  const response = responses[Math.floor(Math.random() * responses.length)];
  const streamId = 'stream-' + Date.now();

  // Start streaming
  state.isStreaming = true;
  const streamMsg = {
    role: 'assistant',
    content: '',
    id: streamId,
    streaming: true,
    timestamp: Date.now()
  };
  state.messages.push(streamMsg);
  renderMessage(streamMsg);

  // Simulate word-by-word streaming
  const words = response.split(' ');
  let currentIndex = 0;

  const streamInterval = setInterval(() => {
    if (currentIndex < words.length) {
      streamMsg.content += (currentIndex > 0 ? ' ' : '') + words[currentIndex];
      updateStreamingMessage(streamId, streamMsg.content);
      scrollToBottom();
      currentIndex++;
    } else {
      clearInterval(streamInterval);
      finishStreamingMessage(streamId);
      saveMessages();
    }
  }, 50);
}

// ============================================================================
// ACTION CONFIRMATION
// ============================================================================

function showActionConfirmation(data) {
  state.pendingAction = data;
  elements.actionBody.textContent = `Agent wants to: ${data.action} on "${data.target}"`;
  elements.actionOverlay.classList.remove('hidden');
}

function handleActionResponse(approved) {
  if (state.pendingAction && state.ws) {
    state.ws.send(JSON.stringify({
      type: 'action_response',
      actionId: state.pendingAction.actionId,
      approved: approved
    }));
  }
  state.pendingAction = null;
  elements.actionOverlay.classList.add('hidden');
}

// ============================================================================
// TAB STATE
// ============================================================================

async function updateTabState() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      state.currentTab = {
        id: tab.id,
        url: tab.url,
        title: tab.title
      };
      elements.tabInfo.textContent = tab.title || tab.url || 'No tab selected';
    }
  } catch (error) {
    console.error('[RMS Assistant] Error getting tab:', error);
  }
}

function sendTabState() {
  if (state.ws && state.currentTab) {
    state.ws.send(JSON.stringify({
      type: 'tab_state',
      tab: state.currentTab
    }));
  }
}

// ============================================================================
// INPUT HANDLING
// ============================================================================

function autoResizeTextarea() {
  const textarea = elements.messageInput;
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function updateSendButton() {
  const hasContent = elements.messageInput.value.trim() || state.pendingFiles.length > 0;
  elements.sendButton.disabled = !hasContent || state.isStreaming;
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

// Send button click
elements.sendButton.addEventListener('click', () => {
  sendMessage(elements.messageInput.value);
});

// Enter to send, Shift+Enter for newline
elements.messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!elements.sendButton.disabled) {
      sendMessage(elements.messageInput.value);
    }
  }
});

// Auto-resize textarea
elements.messageInput.addEventListener('input', () => {
  autoResizeTextarea();
  updateSendButton();
});

// Action confirmation buttons
elements.actionAllow.addEventListener('click', () => handleActionResponse(true));
elements.actionDeny.addEventListener('click', () => handleActionResponse(false));

// Quick action buttons
elements.quickActions.addEventListener('click', (e) => {
  if (e.target.classList.contains('quick-btn')) {
    const prompt = e.target.dataset.prompt;
    elements.messageInput.value = prompt;
    elements.messageInput.focus();
    // Place cursor at end
    elements.messageInput.setSelectionRange(prompt.length, prompt.length);
    updateSendButton();
    autoResizeTextarea();
  }
});

// ============================================================================
// FILE UPLOAD / DRAG & DROP
// ============================================================================

// Drag and drop handlers
elements.dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  elements.dropOverlay.classList.add('active');
});

elements.dropZone.addEventListener('dragleave', (e) => {
  if (!elements.dropZone.contains(e.relatedTarget)) {
    elements.dropOverlay.classList.remove('active');
  }
});

elements.dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  elements.dropOverlay.classList.remove('active');
  handleFiles(e.dataTransfer.files);
});

// Attach button click
elements.attachButton.addEventListener('click', () => {
  elements.fileInput.click();
});

// File input change
elements.fileInput.addEventListener('change', (e) => {
  handleFiles(e.target.files);
  e.target.value = ''; // Reset so same file can be selected again
});

async function handleFiles(fileList) {
  const maxSize = 10 * 1024 * 1024; // 10MB
  const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];

  for (const file of fileList) {
    if (file.size > maxSize) {
      alert(`File "${file.name}" is too large. Max size is 10MB.`);
      continue;
    }
    if (!allowedTypes.includes(file.type)) {
      alert(`File "${file.name}" is not supported. Use PDF, PNG, or JPG.`);
      continue;
    }

    // Convert to base64
    const base64 = await fileToBase64(file);
    state.pendingFiles.push({
      name: file.name,
      mimeType: file.type,
      base64: base64,
      size: file.size
    });
  }

  updateFilePreview();
  updateSendButton();
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function updateFilePreview() {
  if (state.pendingFiles.length === 0) {
    elements.filePreview.innerHTML = '';
    elements.filePreview.classList.remove('active');
    return;
  }

  elements.filePreview.classList.add('active');
  elements.filePreview.innerHTML = state.pendingFiles.map((f, i) => `
    <div class="file-preview-item">
      <span class="file-icon">${f.mimeType === 'application/pdf' ? '📄' : '🖼️'}</span>
      <span class="file-name">${escapeHtml(f.name)}</span>
      <button class="file-remove" data-index="${i}">×</button>
    </div>
  `).join('');

  // Add remove handlers
  elements.filePreview.querySelectorAll('.file-remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const idx = parseInt(e.target.dataset.index);
      state.pendingFiles.splice(idx, 1);
      updateFilePreview();
      updateSendButton();
    });
  });
}

function clearPendingFiles() {
  state.pendingFiles = [];
  updateFilePreview();
}

// Listen for tab changes
chrome.tabs.onActivated.addListener(updateTabState);
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === 'complete') {
    updateTabState();
  }
});

// Listen for messages from service worker
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'TAB_STATE_UPDATE') {
    state.currentTab = message.tab;
    elements.tabInfo.textContent = message.tab.title || message.tab.url || 'No tab selected';
  }

  if (message.type === 'PAGE_CONTEXT_UPDATE') {
    console.log('[Sidepanel] Page context update:', message.site);
    updateContextBar(message);
  }
});

// ============================================================================
// CONTEXT BAR - Real-time page awareness
// ============================================================================

const contextElements = {
  bar: document.getElementById('contextBar'),
  site: document.getElementById('contextSite'),
  details: document.getElementById('contextDetails'),
  actions: document.getElementById('contextActions')
};

let currentPageContext = null;

/**
 * Update the context bar with new page context
 */
function updateContextBar(context) {
  currentPageContext = context;

  if (!context || context.site === 'unknown') {
    contextElements.bar?.classList.add('hidden');
    return;
  }

  // Show the context bar
  contextElements.bar?.classList.remove('hidden');
  contextElements.bar?.setAttribute('data-site', context.site);

  // Update site label
  const siteLabel = getSiteLabel(context);
  if (contextElements.site) {
    contextElements.site.textContent = siteLabel;
  }

  // Update details
  const details = getContextDetails(context);
  if (contextElements.details) {
    contextElements.details.textContent = details;
  }

  // Update actions
  if (contextElements.actions) {
    contextElements.actions.innerHTML = '';
    const actions = getContextActions(context);
    actions.forEach(action => {
      const btn = document.createElement('button');
      btn.className = `context-action-btn ${action.primary ? 'primary' : ''}`;
      btn.textContent = action.label;
      btn.onclick = () => handleContextAction(action.action, context);
      contextElements.actions.appendChild(btn);
    });
  }
}

/**
 * Get human-readable site label
 */
function getSiteLabel(context) {
  switch (context.site) {
    case 'close_lead':
      return context.companyName || 'Close Lead';
    case 'close_dialer':
      return 'Close Dialer';
    case 'progressive':
      return 'Progressive';
    case 'geico':
      return 'Geico';
    case 'bhhc':
      return 'BHHC';
    case 'jmwilson':
      return 'JM Wilson';
    case 'fmcsa':
      return context.carrierName || 'FMCSA SAFER';
    default:
      return context.site;
  }
}

/**
 * Get context details line
 */
function getContextDetails(context) {
  const parts = [];

  if (context.dotNumber) parts.push(`DOT: ${context.dotNumber}`);
  if (context.mcNumber) parts.push(`MC: ${context.mcNumber}`);
  if (context.contactName) parts.push(context.contactName);
  if (context.phone) parts.push(context.phone);
  if (context.pageType) parts.push(context.pageType);
  if (context.operatingStatus) parts.push(context.operatingStatus);

  return parts.join(' | ') || '';
}

/**
 * Get context-aware action buttons
 */
function getContextActions(context) {
  switch (context.site) {
    case 'close_lead':
      return [
        { label: 'Quote', action: 'start_quote', primary: true },
        { label: 'DOT', action: 'lookup_dot' }
      ];
    case 'close_dialer':
      return [
        { label: 'Lead Info', action: 'get_lead_info' }
      ];
    case 'progressive':
    case 'geico':
    case 'bhhc':
    case 'jmwilson':
      const carrierActions = [];
      if (context.dotNumber) {
        carrierActions.push({ label: 'Copy DOT', action: 'copy_dot' });
      }
      carrierActions.push({ label: 'Back to Close', action: 'back_to_close' });
      return carrierActions;
    case 'fmcsa':
      return [
        { label: 'Copy Info', action: 'copy_fmcsa_info' },
        { label: 'Find in Close', action: 'find_in_close' }
      ];
    default:
      return [];
  }
}

/**
 * Handle context action button clicks
 */
async function handleContextAction(action, context) {
  console.log('[Sidepanel] Context action:', action, context);

  switch (action) {
    case 'start_quote':
      showQuotePanel();
      break;

    case 'lookup_dot':
      if (context.dotNumber) {
        sendMessage(`Look up DOT number ${context.dotNumber}`);
      } else {
        sendMessage('Look up the DOT number for this lead');
      }
      break;

    case 'get_lead_info':
      sendMessage('Get info about the current lead');
      break;

    case 'copy_dot':
      if (context.dotNumber) {
        await navigator.clipboard.writeText(context.dotNumber);
        showToast('DOT copied!');
      }
      break;

    case 'back_to_close':
      chrome.runtime.sendMessage({
        type: 'EXECUTE_BROWSER_ACTION',
        action: { action: 'navigate', url: 'https://app.close.com/' }
      });
      break;

    case 'copy_fmcsa_info':
      const info = [];
      if (context.carrierName) info.push(`Name: ${context.carrierName}`);
      if (context.dotNumber) info.push(`DOT: ${context.dotNumber}`);
      if (context.mcNumber) info.push(`MC: ${context.mcNumber}`);
      if (context.operatingStatus) info.push(`Status: ${context.operatingStatus}`);
      await navigator.clipboard.writeText(info.join('\n'));
      showToast('FMCSA info copied!');
      break;

    case 'find_in_close':
      if (context.dotNumber) {
        sendMessage(`Find lead in Close with DOT ${context.dotNumber}`);
      } else if (context.carrierName) {
        sendMessage(`Find lead in Close named ${context.carrierName}`);
      }
      break;
  }
}

/**
 * Show a brief toast notification
 */
function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    background: #1e293b;
    color: white;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    z-index: 1000;
    animation: fadeInOut 2s ease-in-out forwards;
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2000);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

async function init() {
  console.log('[RMS Assistant] Initializing side panel...');

  // Load message history
  await loadMessages();

  // Get current tab state
  await updateTabState();

  // Connect to agent server
  connectWebSocket();

  // Focus input
  elements.messageInput.focus();
}

// Start
init();

// ============================================================================
// QUOTE FORM FUNCTIONALITY
// ============================================================================

const quoteElements = {
  panel: document.getElementById('quotePanel'),
  form: document.getElementById('quoteForm'),
  formContainer: document.getElementById('quoteFormContainer'),
  nav: document.querySelectorAll('.quote-nav-item'),
  cancelBtn: document.getElementById('quoteCancel'),
  saveBtn: document.getElementById('quoteSave'),
  addTruckBtn: document.getElementById('addTruckBtn'),
  addTrailerBtn: document.getElementById('addTrailerBtn'),
  addDriverBtn: document.getElementById('addDriverBtn'),
  trucksTable: document.getElementById('trucksTable'),
  trailersTable: document.getElementById('trailersTable'),
  driversTable: document.getElementById('driversTable')
};

// Track row counts
let truckCount = 1;
let trailerCount = 1;
let driverCount = 1;

// Current lead data for pre-fill
let currentLeadData = null;

// ============================================================================
// QUOTE PANEL SHOW/HIDE
// ============================================================================

function showQuotePanel() {
  quoteElements.panel.classList.remove('hidden');
  // Try to pre-fill from current Close lead
  prefillFromCurrentLead();
}

function hideQuotePanel() {
  quoteElements.panel.classList.add('hidden');
}

function resetQuoteForm() {
  quoteElements.form.reset();
  // Reset to single rows
  truckCount = 1;
  trailerCount = 1;
  driverCount = 1;
  // Remove extra rows
  document.querySelectorAll('.vehicle-row:not(.header):not([data-vehicle="truck-1"])').forEach(row => {
    if (row.closest('#trucksTable')) row.remove();
  });
  document.querySelectorAll('.vehicle-row:not(.header):not([data-vehicle="trailer-1"])').forEach(row => {
    if (row.closest('#trailersTable')) row.remove();
  });
  document.querySelectorAll('.driver-row:not(.header):not([data-driver="1"])').forEach(row => row.remove());
}

// ============================================================================
// SECTION NAVIGATION
// ============================================================================

quoteElements.nav.forEach(navItem => {
  navItem.addEventListener('click', (e) => {
    e.preventDefault();
    const targetId = navItem.getAttribute('href').substring(1);
    const targetSection = document.getElementById(targetId);

    if (targetSection) {
      // Update active state
      quoteElements.nav.forEach(n => n.classList.remove('active'));
      navItem.classList.add('active');

      // Smooth scroll to section
      targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// Update nav active state on scroll
quoteElements.formContainer?.addEventListener('scroll', () => {
  const sections = document.querySelectorAll('.quote-section');
  const scrollPos = quoteElements.formContainer.scrollTop + 100;

  sections.forEach(section => {
    if (section.offsetTop <= scrollPos && section.offsetTop + section.offsetHeight > scrollPos) {
      quoteElements.nav.forEach(n => n.classList.remove('active'));
      const activeNav = document.querySelector(`.quote-nav-item[href="#${section.id}"]`);
      if (activeNav) activeNav.classList.add('active');
    }
  });
});

// ============================================================================
// ADD ROW FUNCTIONALITY
// ============================================================================

function addTruckRow() {
  truckCount++;
  const row = document.createElement('div');
  row.className = 'vehicle-row';
  row.dataset.vehicle = `truck-${truckCount}`;
  row.innerHTML = `
    <select name="truck${truckCount}Type"><option value="">Type</option><option value="sleeper">Sleeper</option><option value="daycab">Day Cab</option><option value="boxtruck">Box Truck</option><option value="pickup">Pickup</option></select>
    <input type="text" name="truck${truckCount}Year" maxlength="4" placeholder="Year">
    <input type="text" name="truck${truckCount}Make" placeholder="Make">
    <input type="text" name="truck${truckCount}Model" placeholder="Model">
    <input type="text" name="truck${truckCount}Vin" placeholder="VIN">
    <input type="text" name="truck${truckCount}Value" placeholder="Value $">
  `;
  quoteElements.trucksTable.appendChild(row);
}

function addTrailerRow() {
  trailerCount++;
  const row = document.createElement('div');
  row.className = 'vehicle-row';
  row.dataset.vehicle = `trailer-${trailerCount}`;
  row.innerHTML = `
    <select name="trailer${trailerCount}Type"><option value="">Type</option><option value="dryvan">Dry Van</option><option value="flatbed">Flatbed</option><option value="reefer">Reefer</option><option value="tanker">Tanker</option><option value="stepdeck">Step Deck</option></select>
    <input type="text" name="trailer${trailerCount}Year" maxlength="4" placeholder="Year">
    <input type="text" name="trailer${trailerCount}Make" placeholder="Make">
    <input type="text" name="trailer${trailerCount}Model" placeholder="Model">
    <input type="text" name="trailer${trailerCount}Vin" placeholder="VIN">
    <input type="text" name="trailer${trailerCount}Value" placeholder="Value $">
  `;
  quoteElements.trailersTable.appendChild(row);
}

function addDriverRow() {
  driverCount++;
  const row = document.createElement('div');
  row.className = 'driver-row';
  row.dataset.driver = driverCount;
  row.innerHTML = `
    <input type="text" name="driver${driverCount}Name" placeholder="Driver Name">
    <input type="date" name="driver${driverCount}Dob" title="Date of Birth">
    <input type="text" name="driver${driverCount}License" placeholder="License #">
    <input type="text" name="driver${driverCount}State" maxlength="2" placeholder="ST">
    <input type="date" name="driver${driverCount}HireDate" title="Hire Date">
    <input type="text" name="driver${driverCount}Experience" placeholder="Yrs Exp">
  `;
  quoteElements.driversTable.appendChild(row);
}

quoteElements.addTruckBtn?.addEventListener('click', addTruckRow);
quoteElements.addTrailerBtn?.addEventListener('click', addTrailerRow);
quoteElements.addDriverBtn?.addEventListener('click', addDriverRow);

// ============================================================================
// PRE-FILL FROM CURRENT LEAD
// ============================================================================

async function prefillFromCurrentLead() {
  console.log('[Quote] Attempting to pre-fill from current lead...');

  try {
    // Query the active tab directly
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    console.log('[Quote] Current tab:', tab?.url);

    if (!tab) {
      console.log('[Quote] No active tab found');
      return;
    }

    // Check if we're on a Close CRM lead page
    if (tab.url?.includes('app.close.com/lead/')) {
      // Extract lead ID from URL
      const leadMatch = tab.url.match(/lead\/([^\/\?]+)/);
      if (leadMatch) {
        const leadId = leadMatch[1];
        console.log('[Quote] Detected Close lead ID:', leadId);

        // Request lead data from server
        if (state.ws && state.connected) {
          console.log('[Quote] Requesting lead data from server...');
          state.ws.send(JSON.stringify({
            type: 'get_lead_for_quote',
            leadId: leadId
          }));
        } else {
          console.log('[Quote] WebSocket not connected, skipping server request');
        }
      }

      // Also try to extract data from page DOM (via content script)
      console.log('[Quote] Requesting lead data from content script...');
      chrome.tabs.sendMessage(tab.id, { type: 'GET_LEAD_DATA' }, (response) => {
        if (chrome.runtime.lastError) {
          console.log('[Quote] Content script error:', chrome.runtime.lastError.message);
          return;
        }
        if (response?.success && response.data) {
          console.log('[Quote] Got lead data from page:', response.data);
          fillQuoteForm(response.data);
        } else {
          console.log('[Quote] Content script returned:', response);
        }
      });
    } else {
      console.log('[Quote] Not on a Close CRM lead page');
    }
  } catch (error) {
    console.log('[Quote] Error in prefillFromCurrentLead:', error);
  }
}

/**
 * Parse a full address string into components
 * Handles formats like:
 * - "4718 POPLAR LEVEL RD, LOUISVILLE, KY 40213-2402"
 * - "4718 POPLAR LEVEL RDLOUISVILLE, KY 40213-2402" (no space before city)
 * - "123 Main St City, ST 12345"
 */
function parseAddress(fullAddress) {
  if (!fullAddress) return {};

  // Clean up the input
  let addr = fullAddress.trim();

  // Try to extract ZIP first (5 digits or 5+4 format at the end)
  const zipMatch = addr.match(/\s*(\d{5}(?:-\d{4})?)\s*$/);
  let zip = '';
  if (zipMatch) {
    zip = zipMatch[1];
    addr = addr.replace(zipMatch[0], '').trim();
  }

  // Try to extract state (2 letter code before the zip)
  const stateMatch = addr.match(/,?\s*([A-Z]{2})\s*$/i);
  let state = '';
  if (stateMatch) {
    state = stateMatch[1].toUpperCase();
    addr = addr.replace(stateMatch[0], '').trim();
  }

  // Now we should have "street address, city" or "street addresscity"
  // Try comma-separated first
  let street = '';
  let city = '';

  const commaIdx = addr.lastIndexOf(',');
  if (commaIdx > 0) {
    street = addr.substring(0, commaIdx).trim();
    city = addr.substring(commaIdx + 1).trim();
  } else {
    // No comma - try to find where street ends and city begins
    // Common street suffixes
    const streetSuffixes = /\b(ST|STREET|RD|ROAD|AVE|AVENUE|BLVD|BOULEVARD|DR|DRIVE|LN|LANE|CT|COURT|WAY|PL|PLACE|CIR|CIRCLE|HWY|HIGHWAY|PKWY|PARKWAY)\b/i;
    const suffixMatch = addr.match(streetSuffixes);

    if (suffixMatch) {
      // Find the position right after the street suffix
      const suffixEnd = suffixMatch.index + suffixMatch[0].length;
      street = addr.substring(0, suffixEnd).trim();
      city = addr.substring(suffixEnd).trim();
    } else {
      // Fallback: put everything in street
      street = addr;
    }
  }

  return {
    street: street,
    city: city,
    state: state,
    zip: zip
  };
}

function fillQuoteForm(data, overwrite = false) {
  // Helper: only set if field is empty OR overwrite is true
  const setField = (id, value) => {
    const el = document.getElementById(id);
    if (el && value && (overwrite || !el.value)) {
      el.value = value;
    }
  };

  // Company Info
  setField('qCompanyName', data.companyName);

  // Handle address - parse if we only have a combined address
  let address = data.address || '';
  let city = data.city || '';
  let state = data.state || '';
  let zip = data.zip || '';

  // If we have address but missing city/state/zip, try to parse
  if (address && (!city || !state || !zip)) {
    const parsed = parseAddress(address);
    console.log('[Quote] Parsed address:', parsed);

    // Use parsed values if we don't have them
    if (parsed.street) address = parsed.street;
    if (!city && parsed.city) city = parsed.city;
    if (!state && parsed.state) state = parsed.state;
    if (!zip && parsed.zip) zip = parsed.zip;
  }

  setField('qAddress', address);
  setField('qCity', city);
  setField('qState', state);
  setField('qZip', zip);

  setField('qPhone', data.phone);
  setField('qEmail', data.email);
  setField('qDotNumber', data.dotNumber);
  setField('qMcNumber', data.mcNumber);

  // Owner Info
  setField('qOwnerName', data.contactName);

  // Merge into stored data (don't overwrite existing)
  currentLeadData = { ...data, ...currentLeadData };
}

// Handle lead data from server
function handleLeadDataForQuote(data) {
  console.log('[Quote] Received lead data from server:', data);
  if (data.lead) {
    const lead = data.lead;
    const formData = {
      companyName: lead.display_name || lead.name,
      phone: lead.contacts?.[0]?.phones?.[0]?.phone,
      email: lead.contacts?.[0]?.emails?.[0]?.email,
      contactName: lead.contacts?.[0]?.name,
      // Extract address if available
      address: lead.addresses?.[0]?.address_1,
      city: lead.addresses?.[0]?.city,
      state: lead.addresses?.[0]?.state,
      zip: lead.addresses?.[0]?.zipcode,
      // DOT from custom fields
      dotNumber: lead.custom?.['USDOT Number'] || lead.custom?.['cf_dot_number']
    };
    fillQuoteForm(formData);
    currentLeadData = { ...formData, leadId: lead.id };
  }
}

// ============================================================================
// SAVE & EXPORT
// ============================================================================

async function saveAndExportQuote() {
  const formData = new FormData(quoteElements.form);
  const quoteData = Object.fromEntries(formData.entries());

  // Add metadata
  quoteData.createdAt = new Date().toISOString();
  quoteData.leadId = currentLeadData?.leadId;

  console.log('[Quote] Saving quote data:', quoteData);

  // 1. Generate and download PDF
  await exportQuoteToPDF(quoteData);

  // 2. Save to Close CRM as note
  if (currentLeadData?.leadId && state.ws && state.connected) {
    const noteContent = generateQuoteNoteText(quoteData);
    state.ws.send(JSON.stringify({
      type: 'save_quote_note',
      leadId: currentLeadData.leadId,
      note: noteContent
    }));
  }

  // Show success
  alert('Quote saved! PDF downloaded and note added to lead.');
  hideQuotePanel();
  resetQuoteForm();
}

function generateQuoteNoteText(data) {
  let note = `=== QUOTE FORM - ${new Date().toLocaleDateString()} ===\n\n`;

  note += `COMPANY: ${data.companyName || 'N/A'}\n`;
  note += `DOT#: ${data.dotNumber || 'N/A'} | MC#: ${data.mcNumber || 'N/A'}\n`;
  note += `Address: ${data.address || ''}, ${data.city || ''} ${data.state || ''} ${data.zip || ''}\n`;
  note += `Phone: ${data.phone || 'N/A'} | Email: ${data.email || 'N/A'}\n`;
  note += `Effective Date: ${data.effectiveDate || 'TBD'}\n\n`;

  note += `OWNER: ${data.ownerName || 'N/A'}\n`;
  if (data.ownerIsDriver) note += `- Owner is driver\n`;
  if (data.ownerHasCdl) note += `- Has CDL (issued ${data.cdlYearIssued || 'N/A'})\n`;
  note += `\n`;

  note += `OPERATIONS:\n`;
  note += `- Goods: ${data.goodsHauled || 'N/A'}\n`;
  note += `- Radius: ${data.radius || 'N/A'}\n`;
  if (data.hasEld) note += `- ELD: ${data.eldProvider || 'Yes'}\n`;
  if (data.amazonWork) note += `- Amazon work\n`;
  if (data.refrigeratedGoods) note += `- Refrigerated\n`;
  note += `\n`;

  // Vehicles
  note += `VEHICLES:\n`;
  for (let i = 1; i <= truckCount; i++) {
    const type = data[`truck${i}Type`];
    const year = data[`truck${i}Year`];
    const make = data[`truck${i}Make`];
    if (type || year || make) {
      note += `- Truck ${i}: ${year || ''} ${make || ''} ${data[`truck${i}Model`] || ''} (${type || 'N/A'}) VIN: ${data[`truck${i}Vin`] || 'N/A'} Value: ${data[`truck${i}Value`] || 'N/A'}\n`;
    }
  }
  for (let i = 1; i <= trailerCount; i++) {
    const type = data[`trailer${i}Type`];
    const year = data[`trailer${i}Year`];
    const make = data[`trailer${i}Make`];
    if (type || year || make) {
      note += `- Trailer ${i}: ${year || ''} ${make || ''} ${data[`trailer${i}Model`] || ''} (${type || 'N/A'}) VIN: ${data[`trailer${i}Vin`] || 'N/A'} Value: ${data[`trailer${i}Value`] || 'N/A'}\n`;
    }
  }
  note += `\n`;

  // Drivers
  note += `DRIVERS:\n`;
  for (let i = 1; i <= driverCount; i++) {
    const name = data[`driver${i}Name`];
    if (name) {
      note += `- ${name} | DOB: ${data[`driver${i}Dob`] || 'N/A'} | Lic: ${data[`driver${i}License`] || 'N/A'} (${data[`driver${i}State`] || 'N/A'}) | Exp: ${data[`driver${i}Experience`] || 'N/A'} yrs\n`;
    }
  }
  note += `\n`;

  // Notes
  if (data.liabilityNotes) note += `LIABILITY: ${data.liabilityNotes}\n`;
  if (data.cargoNotes) note += `CARGO: ${data.cargoNotes}\n`;
  if (data.glNotes) note += `G/L: ${data.glNotes}\n`;
  if (data.additionalNotes) note += `NOTES: ${data.additionalNotes}\n`;

  return note;
}

async function exportQuoteToPDF(data) {
  // Create a printable HTML document
  const printContent = generatePrintableQuote(data);

  // Open in new window and trigger print
  const printWindow = window.open('', '_blank', 'width=800,height=600');
  printWindow.document.write(printContent);
  printWindow.document.close();

  // Wait for content to load then print
  printWindow.onload = () => {
    printWindow.print();
  };
}

function generatePrintableQuote(data) {
  return `
<!DOCTYPE html>
<html>
<head>
  <title>Quote - ${data.companyName || 'New Quote'}</title>
  <style>
    body { font-family: Arial, sans-serif; font-size: 12px; padding: 20px; }
    h1 { font-size: 18px; margin-bottom: 5px; }
    h2 { font-size: 14px; background: #2563eb; color: white; padding: 5px 10px; margin: 15px 0 10px 0; }
    .header { text-align: center; margin-bottom: 20px; }
    .row { display: flex; gap: 20px; margin-bottom: 8px; }
    .field { flex: 1; }
    .label { font-weight: bold; color: #666; font-size: 10px; text-transform: uppercase; }
    .value { border-bottom: 1px solid #ccc; min-height: 18px; padding: 2px 0; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    th, td { border: 1px solid #ccc; padding: 5px; text-align: left; font-size: 11px; }
    th { background: #f5f5f5; }
    .checkbox { display: inline-block; width: 12px; height: 12px; border: 1px solid #333; margin-right: 5px; }
    .checkbox.checked { background: #333; }
    @media print { body { padding: 0; } }
  </style>
</head>
<body>
  <div class="header">
    <h1>RISK MANAGEMENT SERVICES, LLC</h1>
    <div>Trucking Quote Form</div>
  </div>

  <div class="row">
    <div class="field" style="flex:2"><div class="label">Company Name</div><div class="value">${data.companyName || ''}</div></div>
    <div class="field"><div class="label">Effective Date</div><div class="value">${data.effectiveDate || ''}</div></div>
  </div>

  <h2>COMPANY INFO</h2>
  <div class="row">
    <div class="field"><div class="label">Address</div><div class="value">${data.address || ''}</div></div>
  </div>
  <div class="row">
    <div class="field"><div class="label">City</div><div class="value">${data.city || ''}</div></div>
    <div class="field" style="flex:0.5"><div class="label">State</div><div class="value">${data.state || ''}</div></div>
    <div class="field" style="flex:0.5"><div class="label">Zip</div><div class="value">${data.zip || ''}</div></div>
  </div>
  <div class="row">
    <div class="field"><div class="label">Phone</div><div class="value">${data.phone || ''}</div></div>
    <div class="field"><div class="label">Email</div><div class="value">${data.email || ''}</div></div>
  </div>
  <div class="row">
    <div class="field"><div class="label">DOT #</div><div class="value">${data.dotNumber || ''}</div></div>
    <div class="field"><div class="label">MC #</div><div class="value">${data.mcNumber || ''}</div></div>
    <div class="field"><div class="label">EIN/Tax ID</div><div class="value">${data.ein || ''}</div></div>
  </div>

  <h2>OWNER INFO</h2>
  <div class="row">
    <div class="field"><div class="label">Owner Name</div><div class="value">${data.ownerName || ''}</div></div>
    <div class="field"><div class="label">Birth Date</div><div class="value">${data.ownerDob || ''}</div></div>
  </div>
  <div class="row">
    <div class="field"><div class="label">License State</div><div class="value">${data.ownerLicenseState || ''}</div></div>
    <div class="field"><div class="label">License #</div><div class="value">${data.ownerLicenseNumber || ''}</div></div>
  </div>
  <div class="row">
    <div class="field"><span class="checkbox ${data.ownerIsDriver ? 'checked' : ''}"></span> Owner is Driver</div>
    <div class="field"><span class="checkbox ${data.ownerHasCdl ? 'checked' : ''}"></span> Has CDL (Year: ${data.cdlYearIssued || ''})</div>
  </div>

  <h2>OPERATIONS INFO</h2>
  <div class="row">
    <div class="field"><div class="label">Garaging Location</div><div class="value">${data.garagingLocation || ''}</div></div>
  </div>
  <div class="row">
    <div class="field"><div class="label">Goods Hauled</div><div class="value">${data.goodsHauled || ''}</div></div>
    <div class="field"><div class="label">Radius</div><div class="value">${data.radius || ''}</div></div>
  </div>
  <div class="row">
    <div class="field"><span class="checkbox ${data.hasEld ? 'checked' : ''}"></span> ELD: ${data.eldProvider || ''}</div>
    <div class="field"><span class="checkbox ${data.amazonWork ? 'checked' : ''}"></span> Amazon</div>
    <div class="field"><span class="checkbox ${data.refrigeratedGoods ? 'checked' : ''}"></span> Refrigerated</div>
  </div>

  <h2>VEHICLES</h2>
  <table>
    <tr><th>Type</th><th>Year</th><th>Make</th><th>Model</th><th>VIN</th><th>Value</th></tr>
    ${generateVehicleRows(data, 'truck', truckCount)}
    ${generateVehicleRows(data, 'trailer', trailerCount)}
  </table>

  <h2>DRIVERS</h2>
  <table>
    <tr><th>Name</th><th>DOB</th><th>License #</th><th>State</th><th>Hire Date</th><th>Experience</th></tr>
    ${generateDriverRows(data, driverCount)}
  </table>

  <h2>COVERAGE NOTES</h2>
  <div class="row"><div class="field"><div class="label">Liability</div><div class="value">${data.liabilityNotes || ''}</div></div></div>
  <div class="row"><div class="field"><div class="label">Cargo</div><div class="value">${data.cargoNotes || ''}</div></div></div>
  <div class="row"><div class="field"><div class="label">G/L</div><div class="value">${data.glNotes || ''}</div></div></div>
  <div class="row"><div class="field"><div class="label">Additional Notes</div><div class="value">${data.additionalNotes || ''}</div></div></div>
</body>
</html>
  `;
}

function generateVehicleRows(data, prefix, count) {
  let rows = '';
  for (let i = 1; i <= count; i++) {
    const type = data[`${prefix}${i}Type`] || '';
    const year = data[`${prefix}${i}Year`] || '';
    const make = data[`${prefix}${i}Make`] || '';
    const model = data[`${prefix}${i}Model`] || '';
    const vin = data[`${prefix}${i}Vin`] || '';
    const value = data[`${prefix}${i}Value`] || '';
    if (type || year || make || vin) {
      rows += `<tr><td>${type}</td><td>${year}</td><td>${make}</td><td>${model}</td><td>${vin}</td><td>${value}</td></tr>`;
    }
  }
  return rows || `<tr><td colspan="6" style="color:#999">No ${prefix}s entered</td></tr>`;
}

function generateDriverRows(data, count) {
  let rows = '';
  for (let i = 1; i <= count; i++) {
    const name = data[`driver${i}Name`] || '';
    const dob = data[`driver${i}Dob`] || '';
    const license = data[`driver${i}License`] || '';
    const driverState = data[`driver${i}State`] || '';
    const hireDate = data[`driver${i}HireDate`] || '';
    const exp = data[`driver${i}Experience`] || '';
    if (name) {
      rows += `<tr><td>${name}</td><td>${dob}</td><td>${license}</td><td>${driverState}</td><td>${hireDate}</td><td>${exp}</td></tr>`;
    }
  }
  return rows || `<tr><td colspan="6" style="color:#999">No drivers entered</td></tr>`;
}

// ============================================================================
// QUOTE EVENT LISTENERS
// ============================================================================

// Start Quote button - find it in quick actions and repurpose
document.querySelectorAll('.quick-btn').forEach(btn => {
  if (btn.textContent.includes('Start Quote')) {
    btn.removeAttribute('data-prompt');
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      showQuotePanel();
    });
  }
});

// Cancel button
quoteElements.cancelBtn?.addEventListener('click', () => {
  if (confirm('Discard this quote?')) {
    hideQuotePanel();
    resetQuoteForm();
  }
});

// Save button
quoteElements.saveBtn?.addEventListener('click', saveAndExportQuote);

// Handle server messages for quote functionality
const originalHandleServerMessage = handleServerMessage;
handleServerMessage = function(data) {
  if (data.type === 'lead_data_for_quote') {
    handleLeadDataForQuote(data);
  } else if (data.type === 'quote_note_saved') {
    console.log('[Quote] Note saved to lead:', data.leadId);
  } else if (data.type === 'carrier_quote_started') {
    updateCarrierStatus(data.carrier, 'started', data.tabId);
  } else if (data.type === 'carrier_quote_progress') {
    updateCarrierStatus(data.carrier, data.status, data.tabId);
  } else {
    originalHandleServerMessage(data);
  }
};

// ============================================================================
// CARRIER QUOTE AUTOMATION
// ============================================================================

// Carrier portal configurations
const CARRIER_CONFIG = {
  progressive: {
    name: 'Progressive',
    loginUrl: 'https://www.foragentsonlylogin.progressive.com/Login/',
    homeUrl: 'https://www.foragentsonly.com/home/',
    requiresLogin: true
  },
  bhhc: {
    name: 'Berkshire Hathaway',
    loginUrl: 'https://bfrms.bhhc.com/',
    homeUrl: 'https://bfrms.bhhc.com/',
    requiresLogin: true
  },
  geico: {
    name: 'Geico',
    loginUrl: 'https://agents.geico.com/',
    homeUrl: 'https://agents.geico.com/',
    requiresLogin: true
  },
  jmwilson: {
    name: 'JM Wilson',
    loginUrl: 'https://www.jmwilson.com/',
    homeUrl: 'https://www.jmwilson.com/',
    requiresLogin: true
  }
};

// Track open carrier tabs
const carrierTabs = new Map();

/**
 * Start a carrier quote - opens portal in background tab
 */
async function startCarrierQuote(carrier) {
  const config = CARRIER_CONFIG[carrier];
  if (!config) {
    console.error('[Carrier] Unknown carrier:', carrier);
    return;
  }

  console.log('[Carrier] Starting quote for:', config.name);

  // Get current quote data
  const quoteData = getQuoteFormData();

  // Update button state
  const btn = document.querySelector(`.carrier-quote-btn[data-carrier="${carrier}"]`);
  if (btn) {
    btn.classList.add('loading');
  }

  // Open carrier portal in background tab
  try {
    const tab = await chrome.tabs.create({
      url: config.loginUrl,
      active: false  // Open in background
    });

    carrierTabs.set(carrier, tab.id);
    console.log('[Carrier] Opened tab:', tab.id, 'for', carrier);

    // Update status
    updateCarrierStatus(carrier, 'Tab opened - waiting for login...', tab.id);

    // Send quote data to agent server for automation
    if (state.ws && state.connected) {
      state.ws.send(JSON.stringify({
        type: 'start_carrier_quote',
        carrier: carrier,
        tabId: tab.id,
        quoteData: quoteData,
        config: config
      }));
    }

    // Mark button as success after short delay
    setTimeout(() => {
      if (btn) {
        btn.classList.remove('loading');
        btn.classList.add('success');
      }
    }, 1000);

  } catch (error) {
    console.error('[Carrier] Error opening tab:', error);
    if (btn) {
      btn.classList.remove('loading');
    }
    updateCarrierStatus(carrier, 'Error: ' + error.message);
  }
}

/**
 * Get all data from the quote form
 */
function getQuoteFormData() {
  const formData = new FormData(quoteElements.form);
  return Object.fromEntries(formData.entries());
}

/**
 * Update carrier status display
 */
function updateCarrierStatus(carrier, status, tabId) {
  const statusEl = document.getElementById('carrierStatus');
  if (!statusEl) return;

  const config = CARRIER_CONFIG[carrier];
  const carrierName = config?.name || carrier;

  // Add or update status line
  let statusItem = statusEl.querySelector(`[data-carrier="${carrier}"]`);
  if (!statusItem) {
    statusItem = document.createElement('div');
    statusItem.className = 'status-item';
    statusItem.dataset.carrier = carrier;
    statusEl.appendChild(statusItem);
  }

  statusItem.innerHTML = `
    <span class="status-icon">→</span>
    <strong>${carrierName}:</strong> ${status}
    ${tabId ? `<a href="#" onclick="chrome.tabs.update(${tabId}, {active: true}); return false;">[view]</a>` : ''}
  `;
}

// Add click handlers for carrier buttons
document.querySelectorAll('.carrier-quote-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const carrier = btn.dataset.carrier;
    startCarrierQuote(carrier);
  });
});
