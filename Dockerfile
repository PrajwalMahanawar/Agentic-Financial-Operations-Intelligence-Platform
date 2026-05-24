FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY manage.py ./
COPY config ./config
COPY investigations ./investigations
COPY ai ./ai
COPY workflows ./workflows

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
