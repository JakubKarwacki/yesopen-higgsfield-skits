"""One Whisper instance per persistent server worker; legacy CLI remains supported."""
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def load_model(name):
    import torch
    import whisper
    threads = os.environ.get('YESOPEN_CPU_THREADS')
    if threads:
        torch.set_num_threads(int(threads))
    device = os.environ.get('YESOPEN_WHISPER_DEVICE')
    options = {'device': device} if device else {}
    if os.environ.get('YESOPEN_OFFLINE') == '1':
        # Do not allow a model download to start behind an active production.
        from pathlib import Path
        cache = Path(os.environ.get('XDG_CACHE_HOME', Path.home()/'.cache'))/'whisper'
        weights = cache/f'{name}.pt'
        if not weights.is_file():
            raise RuntimeError(f'Whisper weights missing: prepare {name} before accepting work')
        import hashlib
        expected = whisper._MODELS[name].split('/')[-2]
        with weights.open('rb') as source:
            checksum = hashlib.file_digest(source, 'sha256').hexdigest()
        if checksum != expected:
            raise RuntimeError('Whisper weight checksum mismatch; prepare verified weights offline')
        return whisper.load_model(str(weights), **options)
    return whisper.load_model(name, **options)
