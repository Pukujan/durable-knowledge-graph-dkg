FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates gh git \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10002 verifier \
    && useradd --uid 10002 --gid 10002 --create-home --shell /usr/sbin/nologin verifier

WORKDIR /opt/fossil-core
COPY pyproject.toml ./
COPY contracts ./contracts
COPY src ./src
COPY scripts ./scripts
RUN python3 -m venv /opt/fossil-venv \
    && /opt/fossil-venv/bin/pip install --no-cache-dir . \
    && install --directory --owner=verifier --group=verifier --mode=0700 /verifier/home

ENV PATH=/opt/fossil-venv/bin:${PATH}
ENTRYPOINT ["/opt/fossil-venv/bin/python", "scripts/run_privileged_local_verifier.py"]
