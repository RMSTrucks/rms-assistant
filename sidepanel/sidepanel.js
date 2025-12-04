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
  wsUrl: 'ws://localhost:8765',  // Agent server WebSocket endpoint
  reconnectDelay: 3000,
  maxReconnectAttempts: 5,
  messageHistoryKey: 'rms_assistant_messages'
};

// State
const state = {
  ws: null,
  connected: false,
  reconnectAttempts: 0,
  messages: [],
  currentTab: null,
  pendingAction: null,
  isStreaming: false
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
  actionDeny: document.getElementById('actionDeny')
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
    div.className = 'tool-usage';
    div.innerHTML = `
      <div class="tool-name">${escapeHtml(message.toolName)}</div>
      ${message.toolResult ? `<div class="tool-result">${escapeHtml(message.toolResult)}</div>` : ''}
    `;
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

function scrollToBottom() {
  elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
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

  state.ws.onerror = (error) => {
    console.error('[RMS Assistant] WebSocket error:', error);
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
      addMessage('assistant', '', {
        type: 'tool',
        toolName: `Using: ${data.tool}`,
        toolResult: data.args ? JSON.stringify(data.args, null, 2) : null
      });
      break;

    case 'tool_result':
      // Update the last tool message with result
      const lastTool = [...state.messages].reverse().find(m => m.type === 'tool');
      if (lastTool) {
        lastTool.toolResult = typeof data.result === 'string'
          ? data.result
          : JSON.stringify(data.result, null, 2);
      }
      break;

    case 'action_request':
      showActionConfirmation(data);
      break;

    case 'error':
      hideThinkingIndicator();
      addMessage('assistant', `Error: ${data.message}`);
      break;
  }
}

async function sendMessage(content) {
  if (!content.trim()) return;

  // Add user message to display
  addMessage('user', content);

  // Clear input
  elements.messageInput.value = '';
  autoResizeTextarea();
  updateSendButton();

  // Show thinking indicator
  showThinkingIndicator();

  if (state.connected && state.ws) {
    // Send to agent server
    state.ws.send(JSON.stringify({
      type: 'message',
      content: content,
      tabState: state.currentTab
    }));
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
  elements.sendButton.disabled = !elements.messageInput.value.trim() || state.isStreaming;
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
});

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
