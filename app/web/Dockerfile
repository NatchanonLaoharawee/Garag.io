# ---- base stage ----
FROM python:3.12-slim AS base

WORKDIR /app

# Install dependencies separately for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ---- development stage ----
FROM base AS development

ENV FLASK_ENV=development
ENV FLASK_DEBUG=1

# Flask dev server with auto-reload
CMD ["flask", "--app", "main.py", "run", "--host", "0.0.0.0", "--port", "8080", "--reload"]

# ---- production stage ----
FROM base AS production

ENV FLASK_ENV=production
ENV FLASK_DEBUG=0

EXPOSE 8080

CMD ["python", "main.py"]
