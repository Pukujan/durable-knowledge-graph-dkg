FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates gh git python3 python3-venv util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 codexworker \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin codexworker \
    && install --directory --owner=codexworker --group=codexworker --mode=0700 /worker/home /worker/codex-home \
    && npm install --global @openai/codex@latest

WORKDIR /opt/fossil-core
COPY pyproject.toml ./
COPY contracts ./contracts
COPY src ./src
COPY scripts ./scripts
RUN python3 -m venv /opt/fossil-venv \
    && /opt/fossil-venv/bin/pip install --no-cache-dir \
        '.[test]' \
        'fastapi>=0.115,<1' \
        'httpx>=0.27,<1' \
        'pyyaml'

COPY docker/trusted-local-broker/worker-codex /usr/local/bin/worker-codex
RUN chmod 0755 /usr/local/bin/worker-codex

ENV PATH=/opt/fossil-venv/bin:${PATH}
HEALTHCHECK --interval=15s --timeout=10s --start-period=10s --retries=2 CMD ["python3", "scripts/run_trusted_local_broker.py", "--config", "/etc/fossil/broker.json", "--health"]
ENTRYPOINT ["/opt/fossil-venv/bin/python", "scripts/run_trusted_local_broker.py"]
