const BACKEND = process.env.REACT_APP_BACKEND || "http://127.0.0.1:8000";
const WS_URL =
  process.env.REACT_APP_WS_URL || `${BACKEND.replace(/^http/, "ws")}/ws`;

function connect(onMessage) {
  let socket = null;
  let reconnectTimer = null;
  let shouldReconnect = true;

  const openSocket = () => {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      console.log("%c[WS] Connected", "color:#00ffcc");
    };

    socket.onmessage = (event) => {
      if (typeof onMessage === "function") {
        onMessage({ text: event.data });
      }
    };

    socket.onerror = () => {
      console.warn("[WS] Error");
    };

    socket.onclose = () => {
      if (!shouldReconnect) return;
      console.log("%c[WS] Disconnected - Reconnecting...", "color:orange");
      reconnectTimer = setTimeout(openSocket, 1000);
    };
  };

  openSocket();

  return {
    get readyState() {
      return socket ? socket.readyState : WebSocket.CLOSED;
    },
    disconnect() {
      shouldReconnect = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socket) socket.close();
    },
  };
}

async function fetchLatestFrame() {
  try {
    const res = await fetch(`${BACKEND}/frames/latest`);
    if (!res.ok) return null;
    const json = await res.json();
    if (!json.png_b64) return null;
    return `data:image/png;base64,${json.png_b64}`;
  } catch {
    return null;
  }
}

export default {
  connect,
  fetchLatestFrame,
  BACKEND,
};
