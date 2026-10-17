FROM python:3.14-slim

RUN apt-get update \
    && apt-get install --yes --no-install-recommends fish \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/bin/fish worker

RUN python -m pip install --no-cache-dir uv

WORKDIR /app
COPY . .
RUN chown --recursive worker:worker /app \
    && mkdir --parents /data \
    && chown worker:worker /data

USER worker
RUN python setup.py

EXPOSE 3050
CMD ["uv", "run", "main.py"]
