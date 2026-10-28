# Pull via a China-reachable registry mirror (docker.io is unreachable from this network)
FROM docker.m.daocloud.io/library/python:3.12-slim

LABEL org.opencontainers.image.title="my-weather"
LABEL org.opencontainers.image.description="Query 5-day weather forecasts from weather.com.cn"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY weather.py .

# Run as an unprivileged user instead of root
RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin weather \
    && chown -R weather:weather /app
USER weather

VOLUME /app/data

ENTRYPOINT ["python", "weather.py"]
CMD ["--help"]
