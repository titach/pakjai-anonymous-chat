import { useEffect, useState } from "react";

// Match every verdict to the exact current draft: late responses never enable a new text.
export function useModeration(text, scope, request, enabled = true) {
  const value = text.trim();
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState(null);
  useEffect(() => {
    if (!enabled || !value) return;
    let active = true;
    const timer = setTimeout(async () => {
      const reply = await request("moderate", { scope, text: value });
      if (active)
        setResult({
          value,
          retry,
          status: reply.ok ? (reply.allowed ? "allowed" : "blocked") : "error",
          message: reply.message,
        });
    }, 650);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [value, scope, request, enabled, retry]);
  const current =
    enabled && result?.value === value && result?.retry === retry
      ? result
      : null;
  const status = !value || !enabled ? "idle" : current?.status || "checking";
  return {
    status,
    allowed: status === "allowed",
    message: current?.message || "",
    retry: () => setRetry((n) => n + 1),
  };
}
