/* =====================================================================
   Nova AI — frontend logic (vanilla ES modules)
   Sections:
     1. State
     2. DOM references
     3. API layer
     4. Rendering helpers
     5. Streaming
     6. Conversation management
     7. Composer (input) behavior
     8. UI wiring / init
   ===================================================================== */

/* ── 1. State ───────────────────────────────────────────────────── */
const state = {
  conversationId: null, // active conversation id (null = unsaved/new)
  personality: "general",
  personalities: [],
  model: "",
  isStreaming: false,
  hasMessages: false,
  messageCount: 0, // messages in the active conversation
  totalTokens: 0, // tokens used this session for the active conversation
};

const MAX_CHARS = 4000;
const PARTICLE_COUNT = 18;

/* ── 2. DOM references ──────────────────────────────────────────── */
const $ = (sel) => document.querySelector(sel);

const dom = {
  particles: $("#particles"),
  sidebar: $("#sidebar"),
  sidebarBackdrop: $("#sidebarBackdrop"),
  menuBtn: $("#menuBtn"),
  sidebarClose: $("#sidebarClose"),
  newChatBtn: $("#newChatBtn"),
  historyList: $("#historyList"),
  historyEmpty: $("#historyEmpty"),
  settingsBtn: $("#settingsBtn"),
  settingsModal: $("#settingsModal"),
  settingModel: $("#settingModel"),
  personaSelector: $("#personaSelector"),
  personaBadge: $("#personaBadge"),
  messageBadge: $("#messageBadge"),
  messageCount: $("#messageCount"),
  tokenBadge: $("#tokenBadge"),
  tokenCount: $("#tokenCount"),
  statMessages: $("#statMessages"),
  statTokens: $("#statTokens"),
  clearBtn: $("#clearBtn"),
  messages: $("#messages"),
  welcome: $("#welcome"),
  thread: $("#thread"),
  suggestions: $("#suggestions"),
  composerForm: $("#composerForm"),
  input: $("#input"),
  sendBtn: $("#sendBtn"),
  charCounter: $("#charCounter"),
  toast: $("#toast"),
};

/* ── 3. API layer ───────────────────────────────────────────────── */
const api = {
  async meta() {
    const res = await fetch("/api/meta");
    if (!res.ok) throw new Error("Failed to load metadata");
    return res.json();
  },
  async listConversations() {
    const res = await fetch("/api/conversations");
    if (!res.ok) throw new Error("Failed to load conversations");
    return res.json();
  },
  async getConversation(id) {
    const res = await fetch(`/api/conversations/${id}`);
    if (!res.ok) throw new Error("Failed to load conversation");
    return res.json();
  },
  async deleteConversation(id) {
    const res = await fetch(`/api/conversations/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete conversation");
    return res.json();
  },
  // Returns the raw streaming Response so the caller can read the body.
  chat(payload) {
    return fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
};

/* ── 4. Rendering helpers ───────────────────────────────────────── */
const formatTime = (date = new Date()) =>
  date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

const escapeHtml = (text) =>
  text.replace(/[&<>"']/g, (ch) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch])
  );

/** Toggle the welcome screen vs. the message thread. */
function setHasMessages(value) {
  state.hasMessages = value;
  dom.welcome.hidden = value;
}

/** Build and append a message row. Returns the bubble element. */
function appendMessage(role, content, timestamp) {
  setHasMessages(true);

  const row = document.createElement("article");
  row.className = `message message--${role}`;

  const avatar = document.createElement("div");
  avatar.className = "message__avatar";
  avatar.textContent = role === "user" ? "You" : "AI";

  const body = document.createElement("div");
  body.className = "message__body";

  const bubble = document.createElement("div");
  bubble.className = "message__bubble";
  if (content) bubble.textContent = content;

  const meta = document.createElement("div");
  meta.className = "message__meta";

  const time = document.createElement("span");
  time.textContent = timestamp ? formatTime(new Date(timestamp)) : formatTime();

  const copyBtn = document.createElement("button");
  copyBtn.className = "message__copy";
  copyBtn.type = "button";
  copyBtn.innerHTML = `
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg> Copy`;
  copyBtn.addEventListener("click", () => copyMessage(bubble, copyBtn));

  meta.append(time, copyBtn);
  body.append(bubble, meta);
  row.append(avatar, body);
  dom.thread.appendChild(row);
  scrollToBottom();

  state.messageCount += 1;
  updateStats({ pop: true });

  return bubble;
}

/** Create an assistant row showing the animated typing indicator. */
function appendTypingRow() {
  setHasMessages(true);

  const row = document.createElement("article");
  row.className = "message message--assistant";
  row.dataset.typing = "true";

  const avatar = document.createElement("div");
  avatar.className = "message__avatar";
  avatar.textContent = "AI";

  const body = document.createElement("div");
  body.className = "message__body";

  const bubble = document.createElement("div");
  bubble.className = "message__bubble";
  bubble.innerHTML = `
    <span class="thinking">
      <span class="thinking__label">Thinking</span>
      <span class="typing"><span></span><span></span><span></span></span>
    </span>`;

  body.appendChild(bubble);
  row.append(avatar, body);
  dom.thread.appendChild(row);
  scrollToBottom();

  return { row, bubble };
}

async function copyMessage(bubble, btn) {
  try {
    await navigator.clipboard.writeText(bubble.textContent);
    const original = btn.innerHTML;
    btn.innerHTML = "Copied!";
    setTimeout(() => (btn.innerHTML = original), 1400);
  } catch {
    showToast("Couldn't copy to clipboard");
  }
}

function scrollToBottom() {
  dom.messages.scrollTop = dom.messages.scrollHeight;
}

function showToast(message) {
  dom.toast.textContent = message;
  dom.toast.hidden = false;
  requestAnimationFrame(() => dom.toast.classList.add("is-visible"));
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => {
    dom.toast.classList.remove("is-visible");
    setTimeout(() => (dom.toast.hidden = true), 220);
  }, 2200);
}

/** Spawn decorative floating particles with randomized motion. */
function spawnParticles() {
  const fragment = document.createDocumentFragment();
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const p = document.createElement("span");
    p.className = "particle";
    const size = 4 + Math.random() * 12;
    p.style.width = `${size}px`;
    p.style.height = `${size}px`;
    p.style.left = `${Math.random() * 100}%`;
    p.style.setProperty("--drift", `${(Math.random() - 0.5) * 160}px`);
    p.style.animationDuration = `${14 + Math.random() * 16}s`;
    p.style.animationDelay = `${-Math.random() * 20}s`;
    fragment.appendChild(p);
  }
  dom.particles.appendChild(fragment);
}

/** Compact number formatting for badges (e.g. 1.2k). */
function formatCompact(n) {
  if (n < 1000) return String(n);
  return `${(n / 1000).toFixed(n < 10000 ? 1 : 0)}k`;
}

/** Reflect message/token counts in the sidebar panel and topbar badges. */
function updateStats({ pop = false } = {}) {
  dom.statMessages.textContent = state.messageCount;
  dom.statTokens.textContent = formatCompact(state.totalTokens);
  dom.messageCount.textContent = state.messageCount;
  dom.tokenCount.textContent = formatCompact(state.totalTokens);

  if (pop) {
    for (const el of [dom.messageBadge, dom.tokenBadge]) {
      el.classList.remove("badge--pop");
      void el.offsetWidth; // restart the animation
      el.classList.add("badge--pop");
    }
  }
}

function resetStats() {
  state.messageCount = 0;
  state.totalTokens = 0;
  updateStats();
}

/** Replay the viewport fade-in for smooth transitions between views. */
function playViewTransition() {
  dom.messages.classList.remove("is-switching");
  void dom.messages.offsetWidth;
  dom.messages.classList.add("is-switching");
}

/* ── 5. Streaming ───────────────────────────────────────────────── */
/**
 * Send a message and stream the assistant reply.
 * Parses Server-Sent Events (data: {json}) from the response body.
 */
async function sendMessage(text) {
  if (state.isStreaming || !text.trim()) return;

  setStreaming(true);
  appendMessage("user", text);
  resetComposer();

  const typing = appendTypingRow();
  let bubble = null; // becomes the real bubble on first token
  let assembled = "";

  try {
    const res = await api.chat({
      message: text,
      personality: state.personality,
      conversation_id: state.conversationId,
    });

    if (!res.ok || !res.body) {
      throw new Error(`Request failed (${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line.
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith("data:")) continue;
        const event = JSON.parse(line.slice(5).trim());

        if (event.type === "token") {
          if (!bubble) {
            typing.row.remove();
            bubble = appendMessage("assistant", "");
          }
          assembled += event.content;
          bubble.textContent = assembled;
          scrollToBottom();
        } else if (event.type === "done") {
          handleDone(event);
        } else if (event.type === "error") {
          throw new Error(event.message);
        }
      }
    }
  } catch (err) {
    typing.row.remove();
    if (!bubble) bubble = appendMessage("assistant", "");
    bubble.textContent = assembled || `⚠️ ${err.message}`;
    if (!assembled) bubble.style.color = "#fca5a5";
    showToast(err.message);
  } finally {
    setStreaming(false);
  }
}

function handleDone(event) {
  if (event.usage && typeof event.usage.total === "number") {
    state.totalTokens += event.usage.total;
    updateStats({ pop: true });
  }
  // A new conversation was created server-side: adopt its id and refresh list.
  if (event.conversation_id && event.conversation_id !== state.conversationId) {
    state.conversationId = event.conversation_id;
    loadConversations();
  } else if (event.conversation_id) {
    loadConversations();
  }
}

function setStreaming(value) {
  state.isStreaming = value;
  updateSendButton();
}

/* ── 6. Conversation management ─────────────────────────────────── */
async function loadConversations() {
  try {
    const conversations = await api.listConversations();
    renderHistory(conversations);
  } catch {
    /* non-fatal: sidebar simply stays empty */
  }
}

function renderHistory(conversations) {
  dom.historyList.innerHTML = "";
  dom.historyEmpty.hidden = conversations.length > 0;

  for (const convo of conversations) {
    const item = document.createElement("li");
    item.className = "history-item";
    if (convo.id === state.conversationId) item.classList.add("is-active");

    const title = document.createElement("span");
    title.className = "history-item__title";
    title.textContent = convo.title || "Untitled";

    const del = document.createElement("button");
    del.className = "history-item__delete";
    del.type = "button";
    del.setAttribute("aria-label", "Delete conversation");
    del.innerHTML = `
      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"
              stroke-linecap="round" stroke-linejoin="round" />
      </svg>`;

    item.addEventListener("click", () => openConversation(convo.id));
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      removeConversation(convo.id);
    });

    item.append(title, del);
    dom.historyList.appendChild(item);
  }
}

async function openConversation(id) {
  if (state.isStreaming) return;
  try {
    const data = await api.getConversation(id);
    state.conversationId = id;
    dom.thread.innerHTML = "";
    setHasMessages(false);
    resetStats();
    playViewTransition();

    for (const msg of data.messages) {
      appendMessage(msg.role, msg.content, msg.created_at);
    }
    closeSidebar();
    await loadConversations();
  } catch {
    showToast("Couldn't open conversation");
  }
}

async function removeConversation(id) {
  try {
    await api.deleteConversation(id);
    if (id === state.conversationId) startNewChat();
    await loadConversations();
    showToast("Conversation deleted");
  } catch {
    showToast("Couldn't delete conversation");
  }
}

function startNewChat() {
  state.conversationId = null;
  dom.thread.innerHTML = "";
  setHasMessages(false);
  resetStats();
  playViewTransition();
  loadConversations();
  dom.input.focus();
}

/* ── 7. Composer behavior ───────────────────────────────────────── */
function autosize() {
  dom.input.style.height = "auto";
  dom.input.style.height = `${Math.min(dom.input.scrollHeight, 200)}px`;
}

function updateCounter() {
  const len = dom.input.value.length;
  dom.charCounter.textContent = `${len} / ${MAX_CHARS}`;
  dom.charCounter.classList.toggle("is-warning", len > MAX_CHARS * 0.9);
  updateSendButton();
}

function updateSendButton() {
  const hasText = dom.input.value.trim().length > 0;
  dom.sendBtn.disabled = !hasText || state.isStreaming;
}

function resetComposer() {
  dom.input.value = "";
  autosize();
  updateCounter();
}

/* ── 8. Personality selector ────────────────────────────────────── */
function renderPersonalities() {
  dom.personaSelector.innerHTML = "";
  for (const p of state.personalities) {
    const btn = document.createElement("button");
    btn.className = "persona__btn";
    btn.type = "button";
    btn.role = "tab";
    btn.textContent = p.name;
    btn.dataset.id = p.id;
    if (p.id === state.personality) btn.classList.add("is-active");
    btn.addEventListener("click", () => selectPersonality(p));
    dom.personaSelector.appendChild(btn);
  }
}

function selectPersonality(p) {
  state.personality = p.id;
  dom.personaBadge.textContent = p.name;
  dom.personaSelector.querySelectorAll(".persona__btn").forEach((btn) =>
    btn.classList.toggle("is-active", btn.dataset.id === p.id)
  );
}

/* ── 9. Sidebar (mobile) + modal ────────────────────────────────── */
function openSidebar() {
  dom.sidebar.classList.add("is-open");
  dom.sidebarBackdrop.hidden = false;
}
function closeSidebar() {
  dom.sidebar.classList.remove("is-open");
  dom.sidebarBackdrop.hidden = true;
}
function openModal() {
  dom.settingsModal.hidden = false;
}
function closeModal() {
  dom.settingsModal.hidden = true;
}

/* ── 10. Init / wiring ──────────────────────────────────────────── */
function bindEvents() {
  // Composer
  dom.composerForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage(dom.input.value);
  });
  dom.input.addEventListener("input", () => {
    autosize();
    updateCounter();
  });
  dom.input.addEventListener("keydown", (e) => {
    // Enter sends; Shift+Enter inserts a newline.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(dom.input.value);
    }
  });

  // Suggestions
  dom.suggestions.addEventListener("click", (e) => {
    const card = e.target.closest(".suggestion");
    if (card) sendMessage(card.dataset.prompt);
  });

  // Sidebar + chat controls
  dom.newChatBtn.addEventListener("click", startNewChat);
  dom.clearBtn.addEventListener("click", startNewChat);
  dom.menuBtn.addEventListener("click", openSidebar);
  dom.sidebarClose.addEventListener("click", closeSidebar);
  dom.sidebarBackdrop.addEventListener("click", closeSidebar);

  // Settings modal
  dom.settingsBtn.addEventListener("click", openModal);
  dom.settingsModal.querySelectorAll("[data-close-modal]").forEach((el) =>
    el.addEventListener("click", closeModal)
  );
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeModal();
      closeSidebar();
    }
  });
}

async function init() {
  bindEvents();
  spawnParticles();
  updateCounter();
  updateStats();

  try {
    const meta = await api.meta();
    state.personalities = meta.personalities;
    state.personality = meta.default_personality;
    state.model = meta.model;
    dom.settingModel.textContent = meta.model;
    renderPersonalities();
    const current = state.personalities.find((p) => p.id === state.personality);
    if (current) dom.personaBadge.textContent = current.name;
  } catch {
    showToast("Failed to load app metadata");
  }

  await loadConversations();
  dom.input.focus();
}

init();
