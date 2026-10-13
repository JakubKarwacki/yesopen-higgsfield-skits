"""Live refresh of saved workflows: every browser that shows a workflow reloads it when the file on the server changes.

ComfyUI keeps the saved workflows as files in user/default/workflows and does not tell the other open tabs when one
changes. This watches that folder and sends the event `yesopen.workflow_changed` to every connected tab; the
script in web/live_refresh.js reloads the workflow if the tab has no unsaved changes of its own (otherwise it only
says that a newer version exists). No node is added to ComfyUI.
"""
import os
import json
import threading
import time

import folder_paths
from server import PromptServer
from aiohttp import web

NODE_CLASS_MAPPINGS = {}
WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "WEB_DIRECTORY"]

POLL_SECONDS = 1.0


def _workflows_dir():
    return os.path.join(folder_paths.get_user_directory(), "default", "workflows")


@PromptServer.instance.routes.get('/yesopen/project-profile')
async def project_profile(request):
    """The node library is derived from the active project graphs, including subgraphs."""
    root = _workflows_dir()
    allowed = set()
    # API-only utility nodes may not appear in the visual templates.
    manifest = os.path.join(os.path.dirname(root), 'yesopen-node-types.json')
    if os.path.isfile(manifest):
        with open(manifest, encoding='utf-8') as source:
            allowed.update(json.load(source))

    def visit(value):
        if isinstance(value, dict):
            for key in ('type', 'class_type'):
                if isinstance(value.get(key), str):
                    allowed.add(value[key])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    main = os.path.join(root, 'yesopen-skit-pipeline.json')
    if not os.path.isfile(main):
        raise web.HTTPNotFound(text='The YesOpen pipeline has not been installed.')
    for base, _, files in os.walk(root):
        for name in files:
            if name.endswith('.json'):
                with open(os.path.join(base, name), encoding='utf-8') as source:
                    visit(json.load(source))
    return web.json_response({'workflow': 'workflows/yesopen-skit-pipeline.json',
                              'node_types': sorted(allowed)})


def _snapshot(root):
    found = {}
    for base, _, files in os.walk(root):
        for name in files:
            if name.endswith(".json"):
                path = os.path.join(base, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                found[os.path.relpath(path, root).replace(os.sep, "/")] = (st.st_mtime_ns, st.st_size)
    return found


def _watch():
    root = _workflows_dir()
    seen = _snapshot(root)
    pending = {}
    while True:
        time.sleep(POLL_SECONDS)
        now = _snapshot(root)
        for name, stamp in now.items():
            if seen.get(name) == stamp:
                pending.pop(name, None)
            elif pending.get(name) == stamp:          # unchanged for one more poll: the write has finished
                seen[name] = stamp
                pending.pop(name, None)
                PromptServer.instance.send_sync("yesopen.workflow_changed", {"path": name, "mtime": stamp[0] // 1_000_000})
            else:
                pending[name] = stamp
        for name in set(seen) - set(now):
            seen.pop(name, None)
            PromptServer.instance.send_sync("yesopen.workflow_changed", {"path": name, "deleted": True})


threading.Thread(target=_watch, name="yesopen-live-refresh", daemon=True).start()
