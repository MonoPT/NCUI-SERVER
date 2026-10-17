FROM python:3.14-slim

RUN python -m pip install --no-cache-dir uv

WORKDIR /app
COPY . .
RUN mkdir --parents /data
RUN python setup.py

RUN useradd --create-home --shell /usr/bin/fish worker \
    && chown --recursive worker:worker /app /data
USER worker

EXPOSE 3050
CMD ["uv", "run", "main.py"]
