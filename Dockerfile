# Praxis Vogel GmbH – Webseite + Kontaktformular (Railway)
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY . .
RUN useradd --create-home web && chown -R web /app
USER web
CMD ["python", "server.py"]
