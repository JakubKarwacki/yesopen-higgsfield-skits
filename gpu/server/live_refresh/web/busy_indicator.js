// A badge at the top of every ComfyUI tab that says whether somebody is generating: green = free, you can press Run;
// amber = you are running; red = another browser is running (your Run would queue behind it).
// Reads /queue (running and pending jobs, each with the client id of the browser that queued it).
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const POLL_MS = 2500;
const STYLE = {
  free: { bg: "#1f6f3a", text: "● Wolne – można odpalać (nikt nie generuje)" },
  mine: { bg: "#8a6d12", text: "● Generujesz Ty" },
  other: { bg: "#8f2a2a", text: "● Ktoś już generuje – poczekaj" },
};

let badge;

function ensureBadge() {
  if (badge?.isConnected) return badge;
  badge = document.createElement("div");
  badge.id = "yesopen-busy";
  Object.assign(badge.style, {
    position: "fixed", top: "6px", left: "50%", transform: "translateX(-50%)", zIndex: 5000, padding: "5px 14px",
    borderRadius: "14px", font: "600 13px system-ui, sans-serif", color: "#fff", pointerEvents: "none",
    boxShadow: "0 1px 6px rgba(0,0,0,.5)", whiteSpace: "nowrap",
  });
  document.body.appendChild(badge);
  return badge;
}

// jobs = {running: [...], pending: [...]} where a job is [number, prompt_id, prompt, extra_data, outputs]
export function stateOf(running, pending, me) {
  const jobs = [...running, ...pending];
  if (!jobs.length) return { kind: "free", running: 0, pending: 0 };
  const others = jobs.filter((j) => j[3]?.client_id !== me);
  return { kind: others.length ? "other" : "mine", running: running.length, pending: pending.length, others: others.length };
}

function render(st) {
  const el = ensureBadge();
  const style = STYLE[st.kind];
  el.style.background = style.bg;
  const queue = st.running + st.pending;
  const extra = st.kind === "free" ? "" : `  ·  ${st.running} w toku, ${st.pending} w kolejce`;
  el.textContent = style.text + extra;
  el.title = st.kind === "other"
    ? `Inna przeglądarka ma ${st.others} zadań (${queue} razem). Twój Run stanie w kolejce za nimi.`
    : "Stan kolejki ComfyUI, odświeżany co kilka sekund.";
}

async function poll() {
  try {
    const q = await api.fetchApi("/queue").then((r) => r.json());
    render(stateOf(q.queue_running ?? [], q.queue_pending ?? [], api.clientId));
  } catch {
    const el = ensureBadge();
    el.style.background = "#555";
    el.textContent = "● Brak połączenia z serwerem";
  }
}

app.registerExtension({
  name: "yesopen.busyIndicator",
  setup() {
    poll();
    setInterval(poll, POLL_MS);
    api.addEventListener("status", poll);          // sent to every browser when the queue changes
    window.__yesopenBusy = { poll, render, stateOf };
  },
});
