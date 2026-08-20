FROM python:3.12-slim

RUN groupadd --gid 10001 fossil \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin fossil \
    && install --directory --owner=fossil --group=fossil --mode=0750 /var/lib/fossil

WORKDIR /opt/fossil-core
COPY pyproject.toml ./
COPY src ./src
COPY schemas ./schemas
COPY skills ./skills
COPY examples ./examples

RUN python -m venv /opt/fossil-venv \
    && /opt/fossil-venv/bin/pip install --no-cache-dir '.[node]'

ENV PATH=/opt/fossil-venv/bin:${PATH} \
    FOSSIL_REPOSITORY_ROOT=/opt/fossil-core \
    FOSSIL_DATA_ROOT=/var/lib/fossil \
    FOSSIL_PACK_MANIFEST=examples/packs/common/manifest.json \
    FOSSIL_ACTION_HOST=0.0.0.0 \
    FOSSIL_ACTION_PORT=8787 \
    FOSSIL_ACTION_MAX_REQUEST_BYTES=65536

EXPOSE 8787
USER fossil

# Liveness checks only the private TCP listener. It does not require a bearer
# secret and does not weaken the public route allowlist with a health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import socket; s=socket.create_connection(('127.0.0.1',8787),3); s.close()"]

ENTRYPOINT ["fossil-chatgpt-action"]
