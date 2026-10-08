"""One Whisper instance per process, behind one interface for every script (fit_lines, inspect_take, qa_report,
assemble). The transcript only validates text we already have (the approved line) and times its words, so the
default backend is faster-whisper (CTranslate2): int8 on the CPU, greedy decoding, several times faster than
openai-whisper with the same large-v3-turbo weights. load_model(name).transcribe(...) returns the openai-whisper
result shape ({"text", "segments": [{"start", "end", "text", "words": [{"word", "start", "end", "probability"}]}]}),
so the callers do not change.

Environment:
  YESOPEN_ASR            faster (default when faster_whisper is installed) | openai
  YESOPEN_WHISPER_DEVICE cpu | cuda | auto (default auto)
  YESOPEN_ASR_COMPUTE    faster-whisper compute type (default int8 on the CPU, float16 on CUDA)
  YESOPEN_ASR_BEAM       beam size (default 1: greedy is enough to check a known text)
  YESOPEN_CPU_THREADS    CPU threads for either backend
  YESOPEN_OFFLINE=1      no model download: weights must already be cached (and, for openai, checksum-verified)
"""
import os
from functools import lru_cache
from pathlib import Path


def _cache_dir():
    return Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'whisper'


def backend():
    choice = os.environ.get('YESOPEN_ASR', '').strip().lower()
    if choice in ('openai', 'faster'):
        return choice
    try:
        import faster_whisper  # noqa: F401
        return 'faster'
    except ImportError:
        return 'openai'


class _FasterWhisper:
    """faster-whisper behind the openai-whisper transcribe() result shape."""

    def __init__(self, name):
        from faster_whisper import WhisperModel
        device = os.environ.get('YESOPEN_WHISPER_DEVICE') or 'auto'
        compute = os.environ.get('YESOPEN_ASR_COMPUTE') or ('float16' if device == 'cuda' else 'int8')
        threads = int(os.environ.get('YESOPEN_CPU_THREADS') or 0)
        self.beam = int(os.environ.get('YESOPEN_ASR_BEAM') or 1)
        self.model = WhisperModel(name, device=device, compute_type=compute, cpu_threads=threads,
                                  download_root=str(_cache_dir() / 'faster-whisper'),
                                  local_files_only=os.environ.get('YESOPEN_OFFLINE') == '1')

    @staticmethod
    def _samples(path):
        """16 kHz mono float32 decoded by ffmpeg (faster-whisper's own PyAV decoder breaks across PyAV versions)."""
        import subprocess
        import numpy as np
        raw = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                              "-f", "f32le", "-"], check=True, capture_output=True).stdout
        return np.frombuffer(raw, dtype=np.float32).copy()

    def transcribe(self, audio, language=None, word_timestamps=False, condition_on_previous_text=False, **_):
        samples = audio if not isinstance(audio, (str, Path)) else self._samples(audio)
        segments, info = self.model.transcribe(samples, language=language, beam_size=self.beam,
                                               word_timestamps=word_timestamps,
                                               condition_on_previous_text=condition_on_previous_text,
                                               vad_filter=False)
        out = []
        for s in segments:
            words = [{'word': w.word, 'start': w.start, 'end': w.end, 'probability': w.probability}
                     for w in (s.words or [])]
            out.append({'start': s.start, 'end': s.end, 'text': s.text, 'words': words})
        return {'text': ''.join(s['text'] for s in out), 'segments': out, 'language': info.language}


def _load_openai(name):
    import torch
    import whisper
    threads = os.environ.get('YESOPEN_CPU_THREADS')
    if threads:
        torch.set_num_threads(int(threads))
    device = os.environ.get('YESOPEN_WHISPER_DEVICE')
    options = {'device': device} if device and device != 'auto' else {}
    if os.environ.get('YESOPEN_OFFLINE') == '1':
        # Do not allow a model download to start behind an active production.
        weights = _cache_dir() / f'{name}.pt'
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


@lru_cache(maxsize=1)
def load_model(name):
    if backend() == 'faster':
        return _FasterWhisper(name)
    return _load_openai(name)
