FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 VESPRA_HOST=0.0.0.0 VESPRA_PORT=8765 VESPRA_MODE=private VESPRA_DB=/data/vespra.sqlite3
WORKDIR /app
RUN groupadd --gid 10001 vespra && useradd --uid 10001 --gid 10001 --no-create-home vespra && mkdir /data && chown 10001:10001 /data
COPY --chown=10001:10001 server.py services.py adapters.py manage.py ./
COPY --chown=10001:10001 ops ./ops
COPY --chown=10001:10001 public ./public
USER 10001:10001
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["python3","-c","import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/healthz',timeout=3)"]
CMD ["python3","server.py"]
