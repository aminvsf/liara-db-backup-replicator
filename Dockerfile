FROM python:3.11-slim AS base

FROM base AS dependencies

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base AS ldbb-replicator

ENV WORKDIR=/usr/src/ldbb-replicator
WORKDIR $WORKDIR
COPY --from=dependencies /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY . .
RUN useradd --uid 1000 ldbb-replicator && \
    chown -R ldbb-replicator:ldbb-replicator $WORKDIR
USER ldbb-replicator
CMD ["python", "src/main.py"]
