# Keep this in sync with backend/Dockerfile.
# Cloud Run source deploys only read a Dockerfile from the source root.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
RUN mkdir -p /app/data
COPY data/fallback_personality.txt ./data/fallback_personality.txt
COPY data/linkedin.pdf ./data/linkedin.pdf
COPY data/style.txt ./data/style.txt
COPY data/summary.txt ./data/summary.txt
COPY data/twin_profile.json ./data/twin_profile.json

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "backend/src"]
