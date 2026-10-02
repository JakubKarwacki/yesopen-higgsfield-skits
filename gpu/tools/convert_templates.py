#!/usr/bin/env python3
"""Convert the pinned UI templates to ComfyUI API format, the way the ComfyUI interface does it.

The UI format (subgraphs, primitive and note nodes, widget lists) is what Comfy-Org publishes; the API format
(one flat dict of executable nodes) is what /prompt accepts. The only correct converter is the interface itself
(`app.graphToPrompt()`), so this script loads every template into a running ComfyUI page in Ego Browser and saves
what the interface would send. Then it applies our small patches (workflows/patches.json).

Needs a ComfyUI of the same version as the server (see workflows/templates.json -> comfyui) with the custom nodes
installed, listening on --comfy (default http://127.0.0.1:8188). It can be the server through the SSH tunnel or a
local CPU install; no models are needed. Without Ego Browser, run the snippet printed by --print-snippet in the
browser console of the ComfyUI page instead.

Usage:
  python3 tools/convert_templates.py [--comfy http://127.0.0.1:8188] [--only talk,tts]
  python3 tools/convert_templates.py --patch-only     # re-apply patches to workflows/api/raw/
"""
import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "workflows" / "templates.json"
UI_DIR = ROOT / "workflows" / "ui"
RAW_DIR = ROOT / "workflows" / "api" / "raw"
API_DIR = ROOT / "workflows" / "api"
PATCHES = ROOT / "workflows" / "patches.json"

READY_CHECK = """
(types) => {
  const app = window.comfyAPI?.app?.app ?? window.app;
  const LG = window.LiteGraph ?? window.comfyAPI?.litegraph?.LiteGraph;
  return Boolean(app?.vueAppReady && types.every((t) => LG?.registered_node_types?.[t]));
}
"""

BROWSER_SNIPPET = """
async ({ template, types, ids }) => {
  const app = window.comfyAPI?.app?.app ?? window.app;
  await app.loadGraphData(template, true, false, null, {
    showMissingNodesDialog: false, showMissingModelsDialog: false,
  });
  const { output } = await app.graphToPrompt();
  const unknown = Object.entries(output).filter(([, node]) =>
    Object.keys(node.inputs).some((name) => name.startsWith("UNKNOWN")));
  if (unknown.length) throw new Error("UNKNOWN inputs in nodes " + unknown.map(([id]) => id).join(", "));
  // The interface restores the previous session's workflow on start-up; if that lands after our load, the active
  // graph is a different one. Every converted node must come from this template.
  const foreign = Object.entries(output).filter(([id, node]) =>
    !ids.includes(id.split(":")[0]) || !types.includes(node.class_type));
  if (!Object.keys(output).length || foreign.length) {
    throw new Error("graph mismatch: " + foreign.slice(0, 5).map(([id, node]) => id + " " + node.class_type).join(", "));
  }
  return output;
}
"""

EGO_SCRIPT = """
// Ego's Node runtime cannot read ~/Documents (macOS privacy), so templates come inline and results go to stdout.
const jobs = __JOBS__;
const task = await taskSpace("convert ComfyUI templates to API format");
const page = task.page("p1");
const results = {};
try {
  await page.goto(__COMFY__);
  for (const job of jobs) {
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        // Converting before the interface registered every node type silently yields inputs named UNKNOWN.
        await page.waitForFunction(__READY__, job.types, { timeout: 60000 });
        results[job.id] = await page.evaluate(__SNIPPET__, { template: job.template, types: job.types, ids: job.ids });
        break;
      } catch (error) {
        results[job.id] = { __error: `attempt ${attempt}: ` + String(error.message ?? error).slice(0, 400) };
        await page.waitForTimeout(2000);
      }
    }
  }
} finally {
  await task.finish({ keep: [] });
}
// One line per template, so one oversized or broken result does not take the others down.
for (const [id, output] of Object.entries(results)) console.log("@@RESULT@@" + JSON.stringify({ id, output }));
"""


VIRTUAL = {"Note", "MarkdownNote", "Reroute", "PrimitiveNode"}


def node_types(template: dict) -> list:
    """Executable node types of a UI template, including those inside subgraphs."""
    subgraphs = (template.get("definitions") or {}).get("subgraphs") or []
    virtual = VIRTUAL | {sg["id"] for sg in subgraphs}
    nodes = list(template["nodes"]) + [n for sg in subgraphs for n in sg["nodes"]]
    return sorted({n["type"] for n in nodes} - virtual)


def top_level_ids(template: dict) -> list:
    """Ids of the template's own nodes; a converted node id starts with one of them ("340:319" is inside node 340)."""
    return sorted(str(n["id"]) for n in template["nodes"] if n["type"] not in VIRTUAL)


def apply_ui_patch(template: dict, steps: list) -> dict:
    """Changes that must happen before conversion, e.g. removing a node the server does not have."""
    template = copy.deepcopy(template)
    for step in steps:
        if step["op"] != "bypass_ui_node":
            raise ValueError(f"unknown ui patch op {step['op']}")
        node_id = step["node"]
        links = template["links"]
        inbound = [link for link in links if link[3] == node_id]
        if len(inbound) != 1:
            raise ValueError(f"node {node_id} needs exactly one input link to bypass")
        origin_id, origin_slot = inbound[0][1], inbound[0][2]
        nodes = {n["id"]: n for n in template["nodes"]}
        origin_links = nodes[origin_id]["outputs"][origin_slot].setdefault("links", [])
        origin_links.remove(inbound[0][0])
        for link in links:
            if link[1] == node_id:  # re-point every consumer to the bypassed node's source
                link[1], link[2] = origin_id, origin_slot
                origin_links.append(link[0])
        template["links"] = [link for link in links if link[0] != inbound[0][0]]
        template["nodes"] = [n for n in template["nodes"] if n["id"] != node_id]
    return template


def apply_patch(prompt: dict, steps: list) -> dict:
    """Apply our documented changes to an API prompt. Each step is one small, named operation."""
    prompt = copy.deepcopy(prompt)
    for step in steps:
        op = step["op"]
        if op == "edit_node":  # e.g. MP3 -> lossless output
            node = prompt[step["node"]]
            node["class_type"] = step.get("class_type", node["class_type"])
            if "title" in step:
                node["_meta"]["title"] = step["title"]
            node["inputs"] = {k: v for k, v in node["inputs"].items() if k not in step.get("drop_inputs", [])}
            node["inputs"].update(step.get("inputs", {}))
        elif op == "bypass":  # remove a node and feed its consumers from the node's own input
            source = prompt[step["node"]]["inputs"][step["input"]]
            del prompt[step["node"]]
            for node in prompt.values():
                for key, value in node["inputs"].items():
                    if isinstance(value, list) and len(value) == 2 and value[0] == step["node"]:
                        node["inputs"][key] = source
        elif op == "add_node":
            if step["node"] in prompt:
                raise ValueError(f"node {step['node']} already exists")
            prompt[step["node"]] = {"class_type": step["class_type"], "inputs": step["inputs"],
                                    "_meta": {"title": step.get("title", step["class_type"])}}
        elif op == "set_input":
            prompt[step["node"]]["inputs"][step["input"]] = step["value"]
        else:
            raise ValueError(f"unknown patch op {op}")
    return prompt


def write_api(templates: list, patches: dict) -> None:
    for template in templates:
        raw = RAW_DIR / f"{template['id']}.json"
        if not raw.exists():
            print(f"{template['id']:12} no raw conversion yet", file=sys.stderr)
            continue
        prompt = json.loads(raw.read_text())
        steps = patches.get(template["id"], {}).get("steps", [])
        final = apply_patch(prompt, steps)
        (API_DIR / f"{template['id']}.json").write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n")
        print(f"{template['id']:12} {len(final):3} nodes, {len(steps)} patch steps")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--comfy", default="http://127.0.0.1:8188")
    parser.add_argument("--only", help="comma-separated template ids")
    parser.add_argument("--patch-only", action="store_true")
    parser.add_argument("--print-snippet", action="store_true", help="print the browser-console converter and exit")
    args = parser.parse_args()
    if args.print_snippet:
        print(BROWSER_SNIPPET.strip())
        return 0

    config = json.loads(CONFIG.read_text())
    templates = config["templates"]
    if args.only:
        wanted = set(args.only.split(","))
        templates = [t for t in templates if t["id"] in wanted]
    patches = json.loads(PATCHES.read_text()) if PATCHES.exists() else {}
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not args.patch_only:
        jobs = []
        for t in templates:
            template = json.loads((UI_DIR / f"{t['name']}.json").read_text())
            template = apply_ui_patch(template, patches.get(t["id"], {}).get("ui_steps", []))
            jobs.append({"id": t["id"], "template": template, "types": node_types(template),
                         "ids": top_level_ids(template)})
        script = (EGO_SCRIPT.replace("__JOBS__", json.dumps(jobs))
                  .replace("__COMFY__", json.dumps(args.comfy))
                  .replace("__READY__", READY_CHECK.strip())
                  .replace("__SNIPPET__", BROWSER_SNIPPET.strip()))
        run = subprocess.run(["ego-browser", "nodejs"], input=script, text=True, capture_output=True)
        # ego-browser prints console.log to stderr, so look at both streams. Split on "\n" only: str.splitlines()
        # also breaks on U+2028 and similar characters, which JSON keeps unescaped inside prompt texts.
        lines = (run.stdout + "\n" + run.stderr).split("\n")
        results = dict(json.loads(line[len("@@RESULT@@"):]).values()
                       for line in lines if line.startswith("@@RESULT@@"))
        if run.returncode != 0 or not results:
            print(run.stdout.strip(), run.stderr.strip(), sep="\n", file=sys.stderr)
            return run.returncode or 1
        failed = 0
        for t in templates:
            if t["id"] not in results:
                print(f"{t['id']:12} FAILED: no result line", file=sys.stderr)
                failed += 1
        for template_id, output in results.items():
            if "__error" in output:
                print(f"{template_id:12} FAILED: {output['__error']}", file=sys.stderr)
                failed += 1
                continue
            (RAW_DIR / f"{template_id}.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
        if failed:
            write_api(templates, patches)
            return 1
    write_api(templates, patches)
    return 0


if __name__ == "__main__":
    sys.exit(main())
