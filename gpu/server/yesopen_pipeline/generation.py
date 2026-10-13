"""Expand project jobs into native ComfyUI nodes using the client's API templates."""
import json
from pathlib import Path

from .contracts import formats, music_plan, prepare_template, safe_file
from .runtime import digest, write_json


def api():
    from . import project_dir, load_audio, load_image, editor, checkpoint, blocked
    return project_dir, load_audio, load_image, editor, checkpoint, blocked


def workflows():
    bundled = Path(__file__).parent / 'workflows'
    return bundled if bundled.is_dir() else Path(__file__).resolve().parents[2] / 'workflows'


def expand(builder, template, values, project, folder, media=None, native_video=None):
    graph, output, resolved, grid = prepare_template(workflows(), template, values)
    media = media or {}
    replacements = {}
    for nid, node in graph.items():
        kind = node['class_type']
        if kind in ('LoadImage', 'LoadAudio', 'LoadVideo'):
            if kind == 'LoadVideo' and native_video is not None:
                replacements[nid] = builder.node('YesOpenVideoPass', video=native_video)
                continue
            key = {'LoadImage': 'image', 'LoadAudio': 'audio', 'LoadVideo': 'file'}[kind]
            path = media.get(key, node['inputs'][key])
            replacements[nid] = builder.node('YesOpenProjectMedia', project=project, path=path,
                                            kind=kind, seconds=grid.get('seconds', 0) if kind == 'LoadAudio' else 0)
        else:
            replacements[nid] = builder.node(kind)
    for nid, node in graph.items():
        if node['class_type'] in ('LoadImage', 'LoadAudio', 'LoadVideo'):
            continue
        for key, value in node['inputs'].items():
            if isinstance(value, list) and len(value) == 2 and value[0] in graph:
                source = graph[value[0]]['class_type']
                slot = {'LoadImage': 0, 'LoadAudio': 1, 'LoadVideo': 2}.get(source, value[1])
                value = replacements[value[0]].out(slot)
            replacements[nid].set_input(key, value)
    for nid, node in graph.items():
        if node['class_type'] in ('CLIPTextEncode', 'MiniMaxH3ImageToVideo'):
            key = 'text' if node['class_type'] == 'CLIPTextEncode' else 'prompt'
            text = replacements[nid].inputs.get(key)
            if text is not None:
                traced = builder.node('YesOpenRecordPrompt', project=project, path=f'{folder}/{nid.replace(":", "-")}.prompt.json', text=text)
                replacements[nid].set_input(key, traced.out(0))
    root = api()[0](project)
    write_json(root / folder / f'{template}.task.json', {'template': template, 'values': resolved,
                                                      'grid': grid, 'graph': graph})
    return replacements[output[0]].out(output[1])


class ProjectMedia:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': ('YESOPEN_PROJECT',), 'path': ('STRING',),
                             'kind': (['LoadImage', 'LoadAudio', 'LoadVideo'],), 'seconds': ('FLOAT',)}}
    RETURN_TYPES = ('IMAGE', 'AUDIO', 'VIDEO')
    FUNCTION = 'run'
    CATEGORY = 'YesOpen/internal'

    @classmethod
    def IS_CHANGED(cls, project, path, kind, seconds):
        source = safe_file(api()[0](project), path)
        return digest(source) if source.is_file() else float('nan')

    def run(self, project, path, kind, seconds):
        project_dir, load_audio, load_image, _, _, blocked = api()
        root = project_dir(project)
        source = safe_file(root, path)
        if kind == 'LoadImage':
            return load_image(source), blocked(), blocked()
        if kind == 'LoadVideo':
            from comfy_api.input_impl import VideoFromFile
            return blocked(), blocked(), VideoFromFile(str(source))
        audio = load_audio(source)
        if seconds:
            import torch
            length = round(seconds * audio['sample_rate'])
            current = audio['waveform'].shape[-1]
            if current > length:
                raise RuntimeError('Shot would truncate approved audio')
            audio['waveform'] = torch.nn.functional.pad(audio['waveform'], (0, length - current))
        return blocked(), audio, blocked()


class RecordPrompt:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': ('YESOPEN_PROJECT',), 'path': ('STRING',), 'text': ('STRING',)}}
    RETURN_TYPES = ('STRING',)
    FUNCTION = 'run'
    CATEGORY = 'YesOpen/internal'
    def run(self, project, path, text):
        write_json(safe_file(api()[0](project), path), {'text': text})
        return (text,)


class GenerateTake:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': ('YESOPEN_PROJECT',), 'line': ('STRING', {'default': 'l01'}), 'audio': ('AUDIO',)}}
    RETURN_TYPES = ('VIDEO',)
    FUNCTION = 'run'
    CATEGORY = 'YesOpen'

    @classmethod
    def IS_CHANGED(cls, **kw):
        return float('nan')

    def run(self, project, line, audio):
        from comfy_execution.graph_utils import GraphBuilder
        root = api()[0](project)
        job = json.loads((root / f'takes/batch-{line}.json').read_text())['jobs'][0]
        values = job['set']
        builder = GraphBuilder()
        result = expand(builder, job['template'], values, project, f'takes/{line}',
                        {'image': str((root / 'takes' / values['image']).resolve().relative_to(root)),
                         'audio': str((root / 'takes' / values['audio']).resolve().relative_to(root))})
        doc = json.loads((root / 'lines.json').read_text())
        entry = next(item for item in doc['lines'] if item['id'] == line)
        post = {**doc.get('take', {}).get('postprocess', {}), **entry.get('postprocess', {})}
        for template in ('upscale', 'interpolate'):
            settings = post.get(template) or {}
            if not settings.get('enabled', False):
                continue
            params = {k: v for k, v in settings.items() if k != 'enabled'}
            if 'multiplier' not in params:
                raise RuntimeError(f'{template}: configure multiplier explicitly')
            params['video'] = 'native-video'
            # The source is already a VIDEO; substitute the loader node after expansion.
            result = expand(builder, template, params, project, f'takes/{line}', native_video=result)
        return {'result': (result,), 'expand': builder.finalize()}


class VideoPass:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'video': ('VIDEO',)}}
    RETURN_TYPES = ('IMAGE', 'AUDIO', 'VIDEO')
    FUNCTION = 'run'
    CATEGORY = 'YesOpen/internal'
    def run(self, video):
        return api()[5](), api()[5](), video


class Cast:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': ('YESOPEN_PROJECT',), 'candidate': ('INT', {'default': 0, 'min': 0}),
                             'generate': ('BOOLEAN', {'default': False})}}
    RETURN_TYPES = ('STRING',)
    OUTPUT_NODE = True
    FUNCTION = 'run'
    CATEGORY = 'YesOpen'
    def run(self, project, candidate, generate):
        if not generate:
            return ('Generowanie kandydatów obsady wyłączone.',)
        from comfy_execution.graph_utils import GraphBuilder
        root = api()[0](project)
        doc = json.loads((root / 'lines.json').read_text())
        builder = GraphBuilder()
        for index, (who, char) in enumerate(doc['characters'].items()):
            if char.get('still') and safe_file(root, char['still']).is_file():
                continue
            if not char.get('look', '').strip():
                raise RuntimeError(f'{who}: brak opisu look do generowania stilla')
            seed = int(char.get('seed', 1000 + 10 * index)) + candidate
            values = {'prompt': char['look'], 'seed': seed, **char.get('still_params', {})}
            values['seed'] = seed
            image = expand(builder, 'still', values, project, f'stills/{who}-{seed}')
            builder.node('YesOpenSaveStill', project=project, who=who, seed=seed, image=image)
        return {'result': ('Kandydaci obsady według postaci.',), 'expand': builder.finalize()}


class SceneVariant:
    """Optional edit/B-roll from a named, explicit scene specification; never a demo prompt."""
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': ('YESOPEN_PROJECT',), 'line': ('STRING', {'default': 'l01'}),
                             'variant': ('STRING', {'default': 'broll'}), 'enabled': ('BOOLEAN', {'default': False})}}
    RETURN_TYPES = ('STRING',)
    OUTPUT_NODE = True
    FUNCTION = 'run'
    CATEGORY = 'YesOpen'
    def run(self, project, line, variant, enabled):
        if not enabled:
            return ('Wariant sceny wyłączony.',)
        from comfy_execution.graph_utils import GraphBuilder
        root = api()[0](project)
        doc = json.loads((root / 'lines.json').read_text())
        entry = next(item for item in doc['lines'] if item['id'] == line)
        job = entry.get('variants', {}).get(variant)
        if not job or not job.get('set', {}).get('prompt', '').strip() or 'seed' not in job.get('set', {}):
            raise RuntimeError(f'{line}.variants.{variant}: required explicit template, prompt and seed')
        template = job['template']
        allowed = {'still-edit', 'h3-i2v', 'h3-r2v', 'action', 'action-t2v', 'action-flf'}
        if template not in allowed or not variant.replace('_', '').replace('-', '').isalnum():
            raise RuntimeError('Unsupported scene variant or identifier')
        builder = GraphBuilder()
        result = expand(builder, template, job['set'], project, f'takes/{line}-{variant}')
        if template == 'still-edit':
            builder.node('YesOpenSaveStill', project=project, who=entry['who'] + '-' + variant,
                         seed=job['set']['seed'], image=result)
        else:
            builder.node('YesOpenSaveTake', project=project, line=line, suffix='-' + variant, video=result)
        return {'result': (f'{line}/{variant}: jawna specyfikacja sceny.',), 'expand': builder.finalize()}


class Music:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': ('YESOPEN_PROJECT',)}}
    RETURN_TYPES = ('YESOPEN_PROJECT', 'STRING')
    FUNCTION = 'run'
    CATEGORY = 'YesOpen'
    def run(self, project):
        from comfy_execution.graph_utils import GraphBuilder
        root = api()[0](project)
        mode, values = music_plan(root)
        if mode == 'off':
            return (project, '')
        if mode == 'existing':
            return (project, str(safe_file(root, values['file'])))
        cfg = json.loads((root / 'project.json').read_text())
        current = cfg['music'].get('file')
        if current:
            path = safe_file(root, current)
            source = path.with_suffix('.source.json')
            data = json.loads(source.read_text()) if source.is_file() else {}
            # Saved values include the API defaults (e.g. instrumental lyrics).
            _, _, resolved, _ = prepare_template(workflows(), 'music', values)
            if path.is_file() and data.get('values') == resolved and data.get('sha256') == digest(path):
                return project, str(path)
        builder = GraphBuilder()
        audio = expand(builder, 'music', values, project, 'music')
        _, _, resolved, _ = prepare_template(workflows(), 'music', values)
        saved = builder.node('YesOpenStoreMusic', project=project, audio=audio, spec=json.dumps(resolved, sort_keys=True))
        return {'result': (saved.out(0), saved.out(1)), 'expand': builder.finalize()}


class StoreMusic:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': ('YESOPEN_PROJECT',), 'audio': ('AUDIO',), 'spec': ('STRING',)}}
    RETURN_TYPES = ('YESOPEN_PROJECT', 'STRING')
    FUNCTION = 'run'
    CATEGORY = 'YesOpen/internal'
    def run(self, project, audio, spec):
        from . import project_dir, save_audio
        import hashlib
        values = json.loads(spec)
        root = project_dir(project)
        key = hashlib.sha256(spec.encode()).hexdigest()[:16]
        path = root / f'music/bed-{key}.flac'
        save_audio(audio, path)
        cfg = json.loads((root / 'project.json').read_text())
        cfg['music'].update(file=str(path.relative_to(root)), bpm=values['bpm'])
        write_json(root / 'project.json', cfg)
        write_json(path.with_suffix('.source.json'), {'values': values, 'sha256': digest(path)})
        return (project, str(path))


class RenderFormats:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': ('YESOPEN_PROJECT',)}}
    RETURN_TYPES = ('YESOPEN_PROJECT', 'STRING')
    FUNCTION = 'run'
    OUTPUT_NODE = True
    CATEGORY = 'YesOpen'
    def run(self, project):
        root, editor = api()[0](project), api()[3]
        selected = formats(root)
        logs = []
        cfg = json.loads((root / 'project.json').read_text())
        switches = ([] if cfg.get('captions', {}).get('enabled', True) else ['--no-captions'])
        switches += [] if cfg.get('music', {}).get('enabled', bool(cfg.get('music'))) else ['--no-music']
        for fmt in selected:
            logs.append(editor(project, 'assemble.py', ['.', '--format', fmt] + switches))
        return project, '\n'.join(logs)[-3000:]


class QAFormats(RenderFormats):
    def run(self, project):
        from . import QAReport
        logs = [QAReport().run(project, fmt, True)['result'][1] for fmt in formats(api()[0](project))]
        return project, '\n'.join(logs)[-3000:]


NODES = {'YesOpenProjectMedia': ProjectMedia, 'YesOpenRecordPrompt': RecordPrompt, 'YesOpenGenerateTake': GenerateTake,
         'YesOpenCast': Cast, 'YesOpenMusic': Music, 'YesOpenStoreMusic': StoreMusic,
         'YesOpenRenderFormats': RenderFormats, 'YesOpenQAFormats': QAFormats, 'YesOpenVideoPass': VideoPass,
         'YesOpenSceneVariant': SceneVariant}
