FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper.py server.py app.py ./

VOLUME ["/data"]
EXPOSE 8080

ENV ROOSTER_JSON_PATH=/data/rooster.json
ENV POORT=8080
ENV SCRAPE_INTERVAL_MINUTEN=15

CMD ["python", "app.py"]
