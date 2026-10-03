# ComfyUI 0.35.0 on PyTorch 2.13 / CUDA 13.0, plus the Chatterbox TTS nodes and what they need. Nothing else.
#
# Base: SaladTechnologies' maintained image (pytorch/pytorch runtime + ComfyUI cloned at the tag + its requirements,
# torch kept at the base version through a constraints file). Pinned by digest, so a rebuild gets the same layers.
FROM ghcr.io/saladtechnologies/comfyui-api:comfy0.35.0-torch2.13.0-cuda13.0-runtime@sha256:5cc4f79f21e61b9da46e94286c29ef8185520117452027a6f5574cf6125c0ff8

ARG CHATTERBOX_REPO=https://github.com/filliptm/ComfyUI_Fill-ChatterBox.git
ARG CHATTERBOX_COMMIT=f7d7a16187430abcaf91a3039b9c83aa9960816a
ARG TORCHCODEC_VERSION=0.17.0

WORKDIR /opt/ComfyUI

# ComfyUI-Manager comes with the base image; we install nodes only here, pinned, so it goes.
RUN rm -rf custom_nodes/ComfyUI-Manager \
 && git clone --filter=blob:none "$CHATTERBOX_REPO" custom_nodes/ComfyUI_Fill-ChatterBox \
 && git -C custom_nodes/ComfyUI_Fill-ChatterBox checkout --detach "$CHATTERBOX_COMMIT" \
 && uv pip install --system --no-cache-dir -c /opt/pytorch-constraints.txt \
      -r custom_nodes/ComfyUI_Fill-ChatterBox/requirements.txt \
 && python -c "import torch, torchaudio; print('torch', torch.__version__, 'torchaudio', torchaudio.__version__)"

# Explicit V3 loader; checked against pinned vendored source, never silently V2.
COPY patch_chatterbox_v3.py /tmp/patch_chatterbox_v3.py
RUN python /tmp/patch_chatterbox_v3.py custom_nodes/ComfyUI_Fill-ChatterBox

# torchaudio 2.9+ reads and writes files only through TorchCodec, which loads the system FFmpeg libraries. The
# base image has neither, and the Chatterbox dialog node saves its voice prompts with torchaudio.save, so without
# them tts-dialog fails as soon as it runs (validation alone does not show it). Ubuntu 24.04 ships FFmpeg 6.1.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/* \
 && uv pip install --system --no-cache-dir -c /opt/pytorch-constraints.txt "torchcodec==$TORCHCODEC_VERSION" \
 && python -c "import torch, torchaudio; torchaudio.save('/tmp/check.wav', torch.zeros(1, 4800), 48000); \
print('torchaudio.save ok,', tuple(torchaudio.load('/tmp/check.wav')[0].shape))" \
 && rm /tmp/check.wav

# Models, inputs, outputs and settings live on the host disk (compose.yaml), so the image stays small and a new
# machine on the kept disk starts without downloading anything.
EXPOSE 8188
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188", "--disable-auto-launch"]
