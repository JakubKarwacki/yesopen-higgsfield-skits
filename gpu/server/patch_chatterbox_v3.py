"""Pin the vendored multilingual loader to V3; fail closed if upstream files drift.

The pinned upstream Resemble loader uses the same T3 architecture and s3gen.pt for
V2 and V3. Fill's vendored loader instead hardcodes V2 in two files. Patch the
filename at build time, retaining existing node controls and workflow compatibility.
"""
import hashlib
import sys
from pathlib import Path

EXPECTED = {'chatterbox_node.py': '3630642f52cc197474697cfecce14c752f74b599c8bb5f6a64ecb0b32f0f95c9', 'local_chatterbox/chatterbox/mtl_tts.py': '873e0045366ebc2e8a33ddc78a034a51695929a2d251655eb59c9b684c27a87d'}
OLD = 't3_mtl23ls_v2.safetensors'
NEW = 't3_mtl23ls_v3.safetensors'


def patched_sources(root):
    results = {}
    for relative, expected in EXPECTED.items():
        path = Path(root) / relative
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f'Chatterbox source mismatch: {relative}; review before updating')
        text = raw.decode().replace('\r\n', '\n')
        if OLD not in text:
            raise ValueError(f'V2 selector missing: {relative}')
        text = text.replace(OLD, NEW)
        if relative == 'chatterbox_node.py':
            call = '    download_chatterbox_models("ResembleAI/chatterbox", mtl_files, local_dir)'
            if text.count(call) != 1:
                raise ValueError('Multilingual preload call changed')
            text = text.replace(call, '''    missing = [name for name in mtl_files if not (local_dir / name).is_file()]
    if missing:
        raise RuntimeError("Chatterbox V3 weights missing; run verified fetch_models first: " + ", ".join(missing))
    print("[YesOpen] Chatterbox Multilingual V3: t3_mtl23ls_v3.safetensors")''')
        compile(text, relative, 'exec')
        results[path] = text
    return results


def main():
    # Validate every input before touching any file; Docker builds from a clean checkout.
    for path, text in patched_sources(sys.argv[1]).items():
        path.write_text(text)
        print('V3 loader patched:', path.name)


if __name__ == '__main__':
    main()
