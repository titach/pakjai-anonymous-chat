import { useCallback, useEffect, useRef, useState } from "react";

const emptySession = { clientId: null, rooms: [], room: null, messages: [] };

export function useChat() {
  const transport = useRef(null);
  const pending = useRef(new Map());
  const [state, setState] = useState({
    ...emptySession,
    ready: false,
    error: "",
    notice: "",
  });
  useEffect(() => {
    let stopped = false;
    let retryTimer;
    let heartbeat;
    let attempts = 0;
    let lastReceived = 0;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/api/ws`;

    function connect() {
      if (stopped) return;
      const socket = new WebSocket(url);
      transport.current = socket;
      socket.onopen = () => {
        if (stopped) return socket.close();
        attempts = 0;
        lastReceived = Date.now();
        heartbeat = window.setInterval(() => {
          // Treat a silent connection as lost, even if TCP hasn't closed yet.
          if (Date.now() - lastReceived > 45000) return socket.close();
          if (socket.readyState === WebSocket.OPEN)
            socket.send(JSON.stringify({ type: "ping" }));
        }, 15000);
      };
      socket.onmessage = ({ data }) => {
        if (stopped || transport.current !== socket) return;
        lastReceived = Date.now();
        let event;
        try {
          event = JSON.parse(data);
        } catch {
          return socket.close();
        }
        if (event.type === "result") {
          const request = pending.current.get(event.requestId);
          if (request) {
            clearTimeout(request.timer);
            pending.current.delete(event.requestId);
            request.resolve(event);
          }
          return;
        }
        if (event.type === "state")
          setState((previous) => ({
            ...previous,
            ...event.payload,
            ready: true,
            error: "",
          }));
        if (event.type === "message")
          setState((previous) => ({
            ...previous,
            messages: [...previous.messages, event.message].slice(-300),
          }));
        if (event.type === "error")
          setState((previous) => ({ ...previous, error: event.message }));
        if (event.type === "notice")
          setState((previous) => ({ ...previous, notice: event.message }));
      };
      socket.onclose = () => {
        window.clearInterval(heartbeat);
        if (stopped || transport.current !== socket) return;
        transport.current = null;
        for (const request of pending.current.values()) {
          clearTimeout(request.timer);
          request.resolve({
            ok: false,
            message: "ขาดการเชื่อมต่อ กรุณาลองใหม่",
          });
        }
        pending.current.clear();
        setState((previous) => ({
          ...previous,
          ...emptySession,
          ready: false,
          error: "ขาดการเชื่อมต่อเซิร์ฟเวอร์ กำลังเชื่อมต่อใหม่…",
          notice: previous.room
            ? "การเชื่อมต่อห้องสิ้นสุดแล้ว เมื่อเชื่อมต่อใหม่กรุณาเลือกหรือสร้างห้องอีกครั้ง"
            : previous.notice,
        }));
        retryTimer = window.setTimeout(
          connect,
          Math.min(1000 * 2 ** attempts++, 10000),
        );
      };
      // onclose owns recovery so errors don't trigger duplicate retry timers.
      socket.onerror = () => socket.close();
    }
    const restore = (event) => {
      if (event.persisted) window.location.reload();
    };
    const shutdown = () => {
      stopped = true;
      for (const request of pending.current.values()) {
        clearTimeout(request.timer);
        request.resolve({ ok: false, message: "การเชื่อมต่อสิ้นสุดแล้ว" });
      }
      pending.current.clear();
      window.clearTimeout(retryTimer);
      window.clearInterval(heartbeat);
      const socket = transport.current;
      transport.current = null;
      if (socket) {
        // React StrictMode may clean up before the handshake finishes.
        socket.onclose = null;
        socket.onerror = null;
        if (socket.readyState === WebSocket.CONNECTING)
          socket.onopen = () => socket.close();
        else socket.close();
      }
    };
    connect();
    window.addEventListener("pagehide", shutdown);
    window.addEventListener("pageshow", restore);
    return () => {
      shutdown();
      window.removeEventListener("pagehide", shutdown);
      window.removeEventListener("pageshow", restore);
    };
  }, []);

  const send = useCallback((type, payload = {}) => {
    const socket = transport.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setState((previous) => ({
        ...previous,
        error: "ยังไม่ได้เชื่อมต่อเซิร์ฟเวอร์ กรุณารอสักครู่",
      }));
      return false;
    }
    setState((previous) => ({ ...previous, error: "", notice: "" }));
    socket.send(JSON.stringify({ type, ...payload }));
    return true;
  }, []);
  const request = useCallback((type, payload = {}) => {
    const socket = transport.current;
    if (!socket || socket.readyState !== WebSocket.OPEN)
      return Promise.resolve({
        ok: false,
        message: "ยังไม่ได้เชื่อมต่อเซิร์ฟเวอร์ กรุณารอสักครู่",
      });
    const requestId = crypto.randomUUID();
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        pending.current.delete(requestId);
        resolve({
          ok: false,
          message: "การตรวจสอบใช้เวลานานเกินไป กรุณาลองใหม่",
        });
        // Cancel this session so an unacknowledged action cannot commit later.
        socket.close();
      }, 15000);
      pending.current.set(requestId, { resolve, timer });
      socket.send(JSON.stringify({ ...payload, type, requestId }));
    });
  }, []);
  return {
    ...state,
    request,
    send,
    clearError: () => setState((previous) => ({ ...previous, error: "" })),
    clearNotice: () => setState((previous) => ({ ...previous, notice: "" })),
  };
}
