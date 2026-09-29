FROM python:3.11-slim

ARG VOICEMEM_COMMIT=de20ffd49bdaeec0217103c8f5315a6073f9590f

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        bash \
        build-essential \
        bzip2 \
        curl \
        ffmpeg \
        git \
        libsndfile1 \
        portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/voicemem

RUN git init . \
    && git remote add origin https://github.com/shakeel-khan0/VoiceMem.git \
    && git fetch --depth 1 origin "${VOICEMEM_COMMIT}" \
    && test "$(git rev-parse FETCH_HEAD)" = "${VOICEMEM_COMMIT}" \
    && git checkout --detach FETCH_HEAD \
    && python -m pip install \
        torch==2.14.0+cpu \
        torchvision==0.29.0+cpu \
        torchaudio==2.11.0+cpu \
        --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install . \
    && rm -rf .git

CMD ["python", "-m", "uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8765"]
