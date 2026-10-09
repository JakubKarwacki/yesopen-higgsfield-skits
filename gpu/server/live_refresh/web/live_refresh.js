// Reload a workflow in this tab when the saved file changes on the server (event from ../__init__.py).
// A tab with unsaved changes is never overwritten: it only shows a message.
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const toast = (severity, summary, detail) =>
  app.extensionManager?.toast?.add({ severity, summary, detail, life: 6000 });

function findWorkflow(path) {
  const store = app.extensionManager?.workflow;
  const open = store?.openWorkflows ?? store?.workflows ?? [];
  return open.find((w) => w.path === `workflows/${path}`);
}

// Load the saved file of the active workflow into this tab, dropping the tab's own unsaved changes (asks first).
async function reloadFromServer() {
  const store = app.extensionManager.workflow;
  const wf = store.activeWorkflow;
  if (!wf?.path?.startsWith("workflows/")) return;
  if (wf.isModified) {
    const ok = await app.extensionManager.dialog?.confirm?.({
      title: "Odśwież z serwera",
      message: "Ta karta ma niezapisane zmiany. Wczytać wersję z serwera i je odrzucić?",
      type: "default",
    });
    if (ok === false || ok === null) return;
  }
  try {
    const graph = await api.getUserData(wf.path.replace(/^\/?/, "")).then((r) => r.json());
    const ds = app.canvas.ds;
    const view = { scale: ds.scale, offset: [...ds.offset] };
    await app.loadGraphData(graph, false, false, wf);
    wf.changeTracker?.reset?.(graph);
    ds.scale = view.scale;
    ds.offset = view.offset;
    app.canvas.setDirty(true, true);
    toast("info", "Workflow odświeżony", `${wf.path} wczytany z serwera.`);
  } catch (err) {
    console.error("[yesopen.liveRefresh]", err);
    toast("error", "Odświeżanie nie powiodło się", String(err));
  }
}

app.registerExtension({
  name: "yesopen.liveRefresh",
  commands: [{ id: "yesopen.reloadFromServer", label: "Odśwież workflow z serwera", icon: "pi pi-refresh", function: reloadFromServer }],
  keybindings: [{ combo: { key: "r", alt: true }, commandId: "yesopen.reloadFromServer" }],
  menuCommands: [{ path: ["Workflow"], commands: ["yesopen.reloadFromServer"] }],
  setup() {
    api.addEventListener("yesopen.workflow_changed", async (event) => {
      const { path, deleted } = event.detail;
      const wf = findWorkflow(path);
      if (!wf || deleted) return;                        // not open in this tab
      if (wf.isModified) {
        toast("warn", "Nowa wersja workflowu", `${path} zmieniono na serwerze; masz niezapisane zmiany, więc go nie nadpisuję.`);
        return;
      }
      try {
        const graph = await api.getUserData(`workflows/${path}`).then((r) => r.json());
        const isActive = app.extensionManager.workflow.activeWorkflow?.path === wf.path;
        if (isActive) {
          // keep the view (zoom and position) the viewer chose
          const ds = app.canvas.ds;
          const view = { scale: ds.scale, offset: [...ds.offset] };
          await app.loadGraphData(graph, false, false, wf);
          ds.scale = view.scale;
          ds.offset = view.offset;
          app.canvas.setDirty(true, true);
        } else {
          await wf.load({ force: true });
        }
        toast("info", "Workflow odświeżony", `${path} zaktualizowany z serwera.`);
      } catch (err) {
        console.error("[yesopen.liveRefresh]", err);
        toast("error", "Odświeżanie nie powiodło się", String(err));
      }
    });
  },
});
