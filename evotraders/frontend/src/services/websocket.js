/**
 * WebSocket Client for Read-Only Connection
 * Handles connection, reconnection, and heartbeat
 */

import { WS_URL } from "../config/constants";

export class ReadOnlyClient {
  constructor(onEvent, { wsUrl = WS_URL, reconnectDelay = 3000, heartbeatInterval = 5000 } = {}) {
    this.onEvent = onEvent;
    this.wsUrl = wsUrl;
    this.baseReconnectDelay = reconnectDelay;
    this.reconnectDelay = reconnectDelay;
    this.maxReconnectDelay = 30000;
    this.heartbeatInterval = heartbeatInterval;
    this.ws = null;
    this.shouldReconnect = false;
    this.reconnectTimer = null;
    this.heartbeatTimer = null;
    this.reconnectAttempts = 0;
    this.lastPongTime = 0;
  }

  connect() {
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;
    this.reconnectDelay = this.baseReconnectDelay;
    this._connect();
  }

  _connect() {
    if (!this.shouldReconnect) {
      return;
    }

    // Clear any existing connection
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close();
      }
      this.ws = null;
    }

    this.ws = new WebSocket(this.wsUrl);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.reconnectDelay = this.baseReconnectDelay;
      this.lastPongTime = Date.now();
      this._safeEmit({ type: "system", content: "Connected to live server" });
      console.log("WebSocket connected");
      this._startHeartbeat();
    };

    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);

        // Update pong time for any message (server is alive)
        this.lastPongTime = Date.now();

        if (msg.type === "pong") {
          return;
        }

        console.log("[WebSocket] Message received:", msg.type || "unknown");
        this._safeEmit(msg);
      } catch (e) {
        console.error("[WebSocket] Parse error:", e);
      }
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    this.ws.onclose = (event) => {
      const code = event.code || "Unknown";
      console.log(`[WebSocket] Connection closed: Code=${code}, WasClean=${event.wasClean}`);

      this._stopHeartbeat();
      this.ws = null;

      // Always attempt reconnect if shouldReconnect is true
      if (this.shouldReconnect) {
        this.reconnectAttempts++;
        // Exponential backoff with cap
        this.reconnectDelay = Math.min(
          this.baseReconnectDelay * Math.pow(1.5, this.reconnectAttempts),
          this.maxReconnectDelay
        );

        this._safeEmit({
          type: "system",
          content: "Try to connect to data server..."
        });

        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
        }

        this.reconnectTimer = setTimeout(() => {
          console.log(`[WebSocket] Reconnect attempt ${this.reconnectAttempts}...`);
          this._connect();
        }, this.reconnectDelay);
      }
    };
  }

  _safeEmit(msg) {
    try {
      this.onEvent(msg);
    } catch (e) {
      console.error("[WebSocket] Error in event handler:", e);
    }
  }

  _startHeartbeat() {
    this._stopHeartbeat();
    this.lastPongTime = Date.now();

    this.heartbeatTimer = setInterval(() => {
      this._sendPing();

      // Check for stale connection (no response in 60s)
      const timeSinceLastPong = Date.now() - this.lastPongTime;
      if (timeSinceLastPong > 60000 && this.ws) {
        console.warn("[WebSocket] Connection appears stale, forcing reconnect");
        this.ws.close();
      }
    }, this.heartbeatInterval);
  }

  _sendPing() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify({ type: "ping" }));
      } catch (e) {
        console.error("Heartbeat send error:", e);
      }
    }
  }

  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        const messageStr = typeof message === "string" ? message : JSON.stringify(message);
        this.ws.send(messageStr);
        return true;
      } catch (e) {
        console.error("Send error:", e);
        return false;
      }
    } else {
      console.warn("WebSocket is not connected, cannot send message");
      return false;
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    this._stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;
      try {
        this.ws.close();
      } catch (e) {
        console.error("Close error:", e);
      }
    }
    this.ws = null;
  }
}

