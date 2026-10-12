// Measures where the ComfyUI frontend (Vue nodes) draws every node and socket of the open pipeline workflow, inside its
// subgraphs too, and saves it as user/default/comfy_geometry.json on the ComfyUI server. Copy that file to
// gpu/tools/comfy_geometry.json and run build_pipeline_graph.py again: graph_layout.Geometry reads it.
// Run it in the browser console of the ComfyUI tab with yesopen-skit-pipeline open; it takes about a minute and moves the
// view (each node is brought on screen so the frontend renders it). Measure again after changing node sizes or templates.
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function measure(nodes) {
    const ds = app.canvas.ds, cv = app.canvas.canvas.getBoundingClientRect();
    const toCanvas = (cx, cy) => [(cx - cv.left) / ds.scale - ds.offset[0], (cy - cv.top) / ds.scale - ds.offset[1]];
    const res = {};
    for (const n of nodes) {
      ds.scale = 1;
      ds.offset = [-n.pos[0] + 300, -n.pos[1] + 150];
      app.canvas.setDirty(true, true);
      await sleep(350);
      const el = document.querySelector(`.lg-node[data-node-id="${n.id}"]`);
      if (!el) continue;
      const r = el.getBoundingClientRect(), tl = toCanvas(r.left, r.top), br = toCanvas(r.right, r.bottom);
      const dots = [...el.querySelectorAll('[data-testid="slot-connection-dot"]')].map((d) => {
        const b = d.getBoundingClientRect(), c = toCanvas((b.left + b.right) / 2, (b.top + b.bottom) / 2);
        let row = d;
        for (let i = 0; i < 4 && row.parentElement && row.textContent.trim() === ""; i++) row = row.parentElement;
        return { x: c[0] - n.pos[0], y: Math.round((c[1] - n.pos[1]) * 10) / 10, t: row.textContent.trim() };
      });
      const mid = (tl[0] + br[0]) / 2 - n.pos[0];
      const ins = dots.filter((d) => d.x < mid), outs = dots.filter((d) => d.x >= mid);
      const named = {}, used = new Set();
      for (const x of n.inputs || []) {          // a socket row shows the input's label (and a widget's value after it)
        let best = -1, bl = 0;
        ins.forEach((d, i) => {
          if (used.has(i)) return;
          for (const c of [x.label, x.localized_name, x.widget?.name, x.name].filter(Boolean))
            if (d.t.startsWith(c) && c.length > bl) { best = i; bl = c.length; }
        });
        if (best >= 0) { used.add(best); named[x.name] = ins[best].y; }
      }
      res[n.id] = { box: [tl[0] - n.pos[0], tl[1] - n.pos[1], br[0] - n.pos[0], br[1] - n.pos[1]].map(Math.round),
                    ins: named, outs: outs.map((d) => d.y) };
    }
    return res;
  }
  const root = app.graph;
  const geo = { root: await measure(root.nodes.filter((n) => n.type !== "Note")), io: {} };
  for (const sg of root.subgraphs.values()) {
    app.canvas.setGraph(root);
    await sleep(400);
    app.canvas.openSubgraph(sg, root.nodes.find((n) => n.type === sg.id));
    await sleep(1500);
    geo[sg.id] = await measure(sg.nodes.filter((n) => !["Note", "MarkdownNote"].includes(n.type)));
    const io = (node) => ({ w: node.boundingRect[2], h: node.boundingRect[3],
                            slots: node.slots.map((s) => s.pos[1] - node.boundingRect[1]) });
    geo.io[sg.id] = { in: io(sg.inputNode), out: io(sg.outputNode) };
  }
  app.canvas.setGraph(root);
  await fetch("/api/userdata/comfy_geometry.json?overwrite=true", { method: "POST", body: JSON.stringify(geo) });
  console.log("[yesopen] comfy_geometry.json saved");
})();
