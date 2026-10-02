# The skit editor: the same ffmpeg, Python and libraries on the Mac (arm64) and on the GPU server (amd64), so the
# edit scripts of the yesopen-higgsfield-skits skill render the same way in both places.
#
# ffmpeg: BtbN's static GPL build of FFmpeg 8.1 (libx264, no drawtext needed: the skill draws all text with Pillow).
# Encoding runs on the CPU on purpose: neither the H200 nor the B200 has NVENC, and libx264 is what the skill's quality settings assume.
FROM python:3.12-slim-bookworm

ARG TARGETARCH
ARG FFMPEG_RELEASE=autobuild-2026-10-01-13-06
ARG FFMPEG_NAME=ffmpeg-n8.1.3-14-g330caae0c1
ARG FFMPEG_SHA256_AMD64=89cca03b81002bef5a48c2e983afa6100e52904052c1c75dfd2090b09b57efee
ARG FFMPEG_SHA256_ARM64=530e45ec30eead6f8a568d4f7ece53c1f622ed4ce126c44d88ca47896d7dfd27

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
 && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "$TARGETARCH" in \
      amd64) arch=linux64; sum="$FFMPEG_SHA256_AMD64" ;; \
      arm64) arch=linuxarm64; sum="$FFMPEG_SHA256_ARM64" ;; \
      *) echo "unsupported architecture $TARGETARCH"; exit 1 ;; \
    esac; \
    file="$FFMPEG_NAME-$arch-gpl-8.1.tar.xz"; \
    curl -fsSL -o /tmp/ffmpeg.tar.xz "https://github.com/BtbN/FFmpeg-Builds/releases/download/$FFMPEG_RELEASE/$file"; \
    echo "$sum  /tmp/ffmpeg.tar.xz" | sha256sum -c -; \
    tar -xJf /tmp/ffmpeg.tar.xz -C /opt; \
    mv "/opt/$FFMPEG_NAME-$arch-gpl-8.1" /opt/ffmpeg; \
    rm /tmp/ffmpeg.tar.xz; \
    /opt/ffmpeg/bin/ffmpeg -hide_banner -version | head -1
ENV PATH=/opt/ffmpeg/bin:$PATH

# The same versions as on the Mac. Whisper runs on the CPU (it only transcribes takes and checks the final mix).
RUN pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir pillow==12.3.0 numpy==2.4.4 openai-whisper==20250625

WORKDIR /work
CMD ["ffmpeg", "-hide_banner", "-version"]
