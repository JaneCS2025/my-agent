"""
Streamlit voice assistant frontend.
Run with: uv run streamlit run src/app.py
"""

import base64
import os
import uuid
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from livekit import api

load_dotenv(".env.local")

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
AGENT_NAME = "my-agent"

_SRC_DIR = Path(__file__).parent


_MIME = {"gif": "image/gif", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
_FALLBACK = "https://api.dicebear.com/9.x/bottts/svg?seed=agent&backgroundColor=b6e3f4"
_ASSETS_DIR = _SRC_DIR / "assets"


def _image_data_url(stem: str) -> str:
    """Return a data URL for src/assets/<stem>.<ext> or src/<stem>.<ext>, else fallback."""
    for directory in (_ASSETS_DIR, _SRC_DIR):
        for ext in ("png", "gif", "jpg", "jpeg", "webp"):
            p = directory / f"{stem}.{ext}"
            if p.exists():
                b64 = base64.b64encode(p.read_bytes()).decode()
                return f"data:{_MIME[ext]};base64,{b64}"
    return _FALLBACK


def _generate_token() -> str:
    room_name = f"room-{uuid.uuid4().hex[:10]}"
    participant_identity = f"user-{uuid.uuid4().hex[:8]}"
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(participant_identity)
        .with_name("User")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .with_room_config(
            api.RoomConfiguration(
                agents=[api.RoomAgentDispatch(agent_name=AGENT_NAME)]
            )
        )
    )
    return token.to_jwt()


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Voice Assistant",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit chrome for a cleaner look
st.markdown(
    """
    <style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── State ──────────────────────────────────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = _generate_token()

token = st.session_state.token
avatar_src = _image_data_url("Vivian")
avatar_talk_src = _image_data_url("Vivian_talk")

# ── LiveKit component ──────────────────────────────────────────────────────────
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f8f9fb;
    height: 100vh;
    overflow: hidden;
    color: #0f172a;
  }

  /* ── Two-column layout ── */
  .layout {
    display: grid;
    grid-template-columns: 340px 1fr;
    height: 100vh;
  }

  /* ── LEFT PANEL ── */
  .left-panel {
    background: white;
    border-right: 1px solid #e9ecef;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 48px 28px 32px;
    text-align: center;
  }

  .avatar-wrapper {
    width: 200px;
    height: 200px;
    border-radius: 50%;
    overflow: hidden;
    background: #f1f5f9;
    margin-bottom: 22px;
    border: 2px solid #e2e8f0;
    transition: border-color 0.3s, box-shadow 0.3s;
    flex-shrink: 0;
  }
  .avatar-wrapper img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .avatar-wrapper.speaking {
    border-color: #3b82f6;
    box-shadow: 0 0 0 6px rgba(59,130,246,0.15);
    animation: pulse-ring 1.4s ease-out infinite;
  }
  @keyframes pulse-ring {
    0%   { box-shadow: 0 0 0 0   rgba(59,130,246,0.25); }
    70%  { box-shadow: 0 0 0 12px rgba(59,130,246,0); }
    100% { box-shadow: 0 0 0 0   rgba(59,130,246,0); }
  }

  .agent-name {
    font-size: 22px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    margin-bottom: 12px;
    color: #0f172a;
  }
  .badge {
    width: 20px; height: 20px;
    background: #3b82f6;
    border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }
  .badge svg { width: 11px; height: 11px; }

  .agent-desc {
    font-size: 14px;
    color: #64748b;
    line-height: 1.6;
    margin-bottom: 20px;
    max-width: 260px;
  }

  .relation-badge {
    font-size: 13px;
    font-weight: 600;
    color: #d97706;
    margin-bottom: 4px;
  }
  .relation-sub {
    font-size: 12px;
    color: #94a3b8;
    margin-bottom: 20px;
  }

  /* ── RIGHT PANEL ── */
  .right-panel {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: #f8f9fb;
  }

  /* ── Messages ── */
  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 32px 28px 16px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .msg-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }
  .msg-row.user {
    flex-direction: row-reverse;
  }

  .msg-avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    overflow: hidden;
    flex-shrink: 0;
    background: #e2e8f0;
  }
  .msg-avatar img { width: 100%; height: 100%; object-fit: cover; }

  .msg-body {
    max-width: 68%;
  }
  .msg-row.user .msg-body { align-items: flex-end; display: flex; flex-direction: column; }

  .msg-bubble {
    font-size: 15px;
    line-height: 1.55;
    color: #1e293b;
    padding: 0;
  }
  .msg-row.user .msg-bubble {
    background: #dbeafe;
    color: #1e293b;
    padding: 10px 16px;
    border-radius: 20px 20px 4px 20px;
    display: inline-block;
  }

  .msg-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 5px;
    opacity: 0.55;
  }
  .msg-meta svg { width: 14px; height: 14px; color: #94a3b8; }

  /* Interim / in-progress transcript */
  .msg-bubble.interim {
    opacity: 0.45;
    font-style: italic;
  }
  .msg-row.user .msg-bubble.interim {
    background: #e8f0fe;
  }

  /* Placeholder */
  .placeholder {
    font-size: 14px;
    color: #94a3b8;
    text-align: center;
    margin: auto;
    padding: 40px 0;
  }

  /* ── Bottom bar ── */
  .bottom-bar {
    padding: 14px 24px 18px;
    background: #f8f9fb;
    border-top: 1px solid #e9ecef;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .input-row {
    display: flex;
    align-items: center;
    background: white;
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
    padding: 0 12px;
    gap: 8px;
    transition: border-color 0.2s;
  }
  .input-row:focus-within { border-color: #94a3b8; }
  .input-row svg { color: #94a3b8; flex-shrink: 0; }

  #chat-input {
    flex: 1;
    border: none;
    outline: none;
    font-size: 15px;
    color: #1e293b;
    background: transparent;
    padding: 13px 4px;
  }
  #chat-input::placeholder { color: #cbd5e1; }

  #send-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px;
    display: flex; align-items: center;
    color: #94a3b8;
    transition: color 0.15s;
  }
  #send-btn:hover { color: #3b82f6; }
  #send-btn svg { width: 20px; height: 20px; }

  #speak-btn {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 13px;
    background: #1e293b;
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
    user-select: none;
    transition: background 0.15s, transform 0.1s;
    outline: none;
  }
  #speak-btn:hover { background: #334155; }
  #speak-btn.active { background: #3b82f6; transform: scale(1.01); }
  #speak-btn svg { width: 18px; height: 18px; }
</style>
</head>
<body>

<div class="layout">

  <!-- ── LEFT PANEL ── -->
  <div class="left-panel">
    <div class="avatar-wrapper" id="avatar-wrapper">
      <img id="avatar-img" src="__AVATAR__" alt="Assistant" />
    </div>

    <div class="agent-name">
      My Assistant
      <span class="badge">
        <svg viewBox="0 0 10 10" fill="none">
          <path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
    </div>

    <p class="agent-desc">
      Your friendly voice assistant. Ask me anything — I'm here to help.
    </p>

    <div class="relation-badge" id="relation-badge">Connecting…</div>
    <div class="relation-sub" id="relation-sub">Waiting for agent</div>

  </div>

  <!-- ── RIGHT PANEL ── -->
  <div class="right-panel">

    <!-- Messages -->
    <div class="messages" id="messages">
      <div class="placeholder" id="placeholder">Conversation will appear here</div>
    </div>

    <!-- Bottom input bar -->
    <div class="bottom-bar">
      <div class="input-row">
        <!-- Mic icon -->
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="18" height="18">
          <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="22"/>
        </svg>
        <input type="text" id="chat-input" placeholder="Send a message…" autocomplete="off" />
        <!-- Send button -->
        <button id="send-btn" aria-label="Send">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>

      <button id="speak-btn" aria-label="Hold to speak">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="22"/>
        </svg>
        Hold to speak (spacebar)
      </button>
    </div>

  </div><!-- /right-panel -->
</div><!-- /layout -->

<script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
<script>
(function () {
  const WS_URL = "__LIVEKIT_URL__";
  const TOKEN  = "__TOKEN__";
  const AVATAR_SRC      = "__AVATAR__";
  const AVATAR_TALK_SRC = "__AVATAR_TALK__";

  const { Room, RoomEvent, Track, ConnectionState } = LivekitClient;
  const room = new Room({ adaptiveStream: true, dynacast: true });

  let msgCount = 0;

  // ── Relation badge ────────────────────────────────────────────────────────
  function setRelation(text, sub) {
    document.getElementById("relation-badge").textContent = text;
    document.getElementById("relation-sub").textContent = sub;
  }

  // ── Append / update message ──────────────────────────────────────────────
  // segmentId: unique id for upsert (interim → final). Pass null for plain appends.
  // isFinal: if false, renders with italic/faded interim style.
  const segmentRows = {}; // segmentId -> { row, bubble, meta }

  function upsertMessage(role, text, segmentId, isFinal) {
    const container = document.getElementById("messages");
    const placeholder = document.getElementById("placeholder");
    if (placeholder) placeholder.remove();

    const isUser = role === "user";

    // Reuse existing row for this segment
    if (segmentId && segmentRows[segmentId]) {
      const { bubble, meta } = segmentRows[segmentId];
      bubble.textContent = text;
      if (isFinal) {
        bubble.classList.remove("interim");
        if (!isUser && !meta.innerHTML) {
          meta.innerHTML = THUMBS_DOWN_SVG;
        }
        msgCount++;
        updateRelation();
      }
      container.scrollTop = container.scrollHeight;
      return;
    }

    if (!segmentId || isFinal) { msgCount++; updateRelation(); }

    const row = document.createElement("div");
    row.className = "msg-row " + role;

    // Avatar
    const av = document.createElement("div");
    av.className = "msg-avatar";
    const img = document.createElement("img");
    img.src = isUser
      ? "https://api.dicebear.com/9.x/notionists/svg?seed=user&backgroundColor=dbeafe"
      : AVATAR_SRC;
    img.alt = isUser ? "You" : "Assistant";
    av.appendChild(img);

    // Body
    const body = document.createElement("div");
    body.className = "msg-body";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble" + (isFinal ? "" : " interim");
    bubble.textContent = text;

    const meta = document.createElement("div");
    meta.className = "msg-meta";
    if (!isUser && isFinal) meta.innerHTML = THUMBS_DOWN_SVG;

    body.appendChild(bubble);
    if (!isUser) body.appendChild(meta);
    row.appendChild(av);
    row.appendChild(body);
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;

    if (segmentId) segmentRows[segmentId] = { row, bubble, meta };
  }

  function updateRelation() {
    const remaining = Math.max(0, 10 - msgCount);
    if (remaining > 0) {
      setRelation("Just met", remaining + " message" + (remaining === 1 ? "" : "s") + " until assistant gets to know you");
    } else {
      setRelation("Getting to know you", "Keep chatting!");
    }
  }

  const THUMBS_DOWN_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/><path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>';

  // ── Remote audio ──────────────────────────────────────────────────────────
  room.on(RoomEvent.TrackSubscribed, (track) => {
    if (track.kind === Track.Kind.Audio) {
      const el = track.attach();
      el.style.display = "none";
      document.body.appendChild(el);
    }
  });
  room.on(RoomEvent.TrackUnsubscribed, (track) => track.detach());

  // ── Speaking animation + image swap ──────────────────────────────────────
  room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
    const localId = room.localParticipant?.identity;
    const agentSpeaking = speakers.some(p => p.identity !== localId);
    document.getElementById("avatar-wrapper").classList.toggle("speaking", agentSpeaking);
    document.getElementById("avatar-img").src = agentSpeaking ? AVATAR_TALK_SRC : AVATAR_SRC;
  });

  // ── STT / TTS transcripts ──────────────────────────────────────────────────
  // TranscriptionReceived fires for both user speech (STT) and agent speech (TTS).
  // Segments arrive as interim (final=false) then finalized (final=true).
  room.on(RoomEvent.TranscriptionReceived, (segments, participant) => {
    const isLocal = participant?.identity === room.localParticipant?.identity;
    const role = isLocal ? "user" : "agent";
    for (const seg of segments) {
      if (!seg.text.trim()) continue;
      upsertMessage(role, seg.text, seg.id, seg.final);
    }
  });

  // ── Connection state ──────────────────────────────────────────────────────
  room.on(RoomEvent.ConnectionStateChanged, (state) => {
    if (state === ConnectionState.Connected) {
      setRelation("Just met", "Start talking to get to know each other");
    } else if (state === ConnectionState.Disconnected) {
      setRelation("Disconnected", "Refresh to reconnect");
    }
  });

  // ── Connect ───────────────────────────────────────────────────────────────
  room.connect(WS_URL, TOKEN).catch((err) => {
    console.error("LiveKit connection error:", err);
    setRelation("Connection failed", err.message || "");
  });

  // ── Text input send ───────────────────────────────────────────────────────
  const input = document.getElementById("chat-input");
  const sendBtn = document.getElementById("send-btn");

  async function sendTextMessage() {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    // Display immediately in the UI
    upsertMessage("user", text, null, true);
    // Send via lk.chat topic — the agent picks this up automatically,
    // interrupts current speech, and generates a voice + transcript reply
    await room.localParticipant.sendText(text, { topic: "lk.chat" });
  }

  sendBtn.addEventListener("click", sendTextMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendTextMessage();
    }
  });

  // ── Push-to-talk ──────────────────────────────────────────────────────────
  let pttActive = false;

  async function startSpeaking() {
    if (pttActive) return;
    pttActive = true;
    await room.localParticipant.setMicrophoneEnabled(true);
    const btn = document.getElementById("speak-btn");
    btn.classList.add("active");
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><circle cx="12" cy="12" r="6"/></svg>' +
      "Speaking…";
  }

  async function stopSpeaking() {
    if (!pttActive) return;
    pttActive = false;
    await room.localParticipant.setMicrophoneEnabled(false);
    const btn = document.getElementById("speak-btn");
    btn.classList.remove("active");
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18">' +
        '<path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>' +
        '<path d="M19 10v2a7 7 0 0 1-14 0v-2"/>' +
        '<line x1="12" y1="19" x2="12" y2="22"/>' +
      '</svg>' +
      "Hold to speak (spacebar)";
  }

  const speakBtn = document.getElementById("speak-btn");
  speakBtn.addEventListener("mousedown",  startSpeaking);
  speakBtn.addEventListener("mouseup",    stopSpeaking);
  speakBtn.addEventListener("mouseleave", stopSpeaking);
  speakBtn.addEventListener("dragstart",  e => e.preventDefault());

  document.addEventListener("keydown", (e) => {
    if (e.code === "Space" && !e.repeat && document.activeElement.tagName !== "INPUT") {
      e.preventDefault();
      startSpeaking();
    }
  });
  document.addEventListener("keyup", (e) => {
    if (e.code === "Space") {
      e.preventDefault();
      stopSpeaking();
    }
  });
})();
</script>
</body>
</html>
"""

html = (
    HTML_TEMPLATE.replace("__AVATAR__", avatar_src)
    .replace("__AVATAR_TALK__", avatar_talk_src)
    .replace("__LIVEKIT_URL__", LIVEKIT_URL)
    .replace("__TOKEN__", token)
)

components.html(html, height=760, scrolling=False)
