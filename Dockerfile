FROM python:3.14-slim

RUN python -m pip install --no-cache-dir uv

WORKDIR /app
COPY . .
RUN python setup.py

EXPOSE 3050
CMD ["uv", "run", "main.py"]
