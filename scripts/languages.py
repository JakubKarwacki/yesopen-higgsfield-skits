"""Language contract shared by TTS, ASR and text QA; no model imports."""
import json
import re
import unicodedata
from pathlib import Path

# Exact language set of the pinned Chatterbox Multilingual implementation.
LANGUAGES = dict(zip(
    'ar da de el en es fi fr he hi it ja ko ms nl no pl pt ru sv sw tr zh'.split(),
    'Arabic Danish German Greek English Spanish Finnish French Hebrew Hindi Italian Japanese Korean Malay Dutch Norwegian Polish Portuguese Russian Swedish Swahili Turkish Chinese'.split()))


def language_code(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('language must be a supported code, e.g. pl, or Polish (pl)')
    value = value.strip().casefold()
    for code, name in LANGUAGES.items():
        if value in {code, name.casefold(), f'{name.casefold()} ({code})'}:
            return code
    raise ValueError(f'unsupported language {value!r}; supported: {", ".join(LANGUAGES)}')


def language_label(value):
    code = language_code(value)
    return f'{LANGUAGES[code]} ({code})'


def project_language(cfg, doc=None):
    """Missing legacy settings inherit; two explicit settings must agree."""
    values = [language_code(d['language']) for d in (cfg, doc or {}) if 'language' in d]
    if len(set(values)) > 1:
        raise ValueError('project.json and lines.json languages disagree')
    return values[0] if values else 'en'


def language_for_path(path, explicit=None):
    if explicit is not None:
        return language_code(explicit)
    path = Path(path).resolve()
    for folder in [path.parent, *path.parent.parents]:
        cfg = folder / 'project.json'
        if cfg.is_file():
            lines = folder / 'lines.json'
            return project_language(json.loads(cfg.read_text()),
                                    json.loads(lines.read_text()) if lines.is_file() else {})
    return 'en'


def normalize(text, language='en', number_aliases=None):
    """Preserve Unicode letters, combining marks and numbers; never erase a script.

    Numbers remain numbers: cardinal/ordinal/currency readings are ambiguous across
    languages. Do not invent an English reading or turn numeric differences into a pass.
    """
    code = language_code(language)
    aliases = number_aliases or {}
    if not isinstance(aliases, dict) or any(not isinstance(k, str) or not k.isdecimal() or not isinstance(v, str) or not v.strip() for k, v in aliases.items()):
        raise ValueError('number_aliases must map digit strings to approved spoken text')
    text = re.sub(r'(?<!\w)\d+(?!\w)', lambda m: aliases.get(m.group(), m.group()), text)
    if code == 'tr':
        text = text.replace('I', 'ı').replace('İ', 'i')
    text = unicodedata.normalize('NFC', unicodedata.normalize('NFC', text).casefold())
    return ''.join(c for c in text if unicodedata.category(c)[0] in 'LMN')


def comparison(text, language='en', number_aliases=None):
    """Character comparison avoids assuming spaces delimit words in all languages."""
    return normalize(text, language, number_aliases)


def require_speech(text, language='en'):
    if not normalize(text, language):
        raise ValueError('speech text must contain letters or numbers')
    return text


def verify_whisper_model(name, language):
    if str(name).endswith('.en') and language_code(language) != 'en':
        raise ValueError('English-only Whisper weights cannot validate this language')
