FROM alpine:3.20 AS kubectl

ARG TARGETARCH=arm64
ARG KUBECTL_VERSION=v1.31.4

RUN wget -qO /kubectl \
      "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
    && chmod 0755 /kubectl

FROM python:3.12-slim AS base

COPY --from=kubectl /kubectl /usr/local/bin/kubectl

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin gateway
USER 10001

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["uvicorn", "gateway.app:app", "--host", "0.0.0.0", "--port", "8000"]
