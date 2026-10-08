FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Africa/Cairo

WORKDIR /usr/src/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

ARG REQUIREMENTS=requirements.txt
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip && pip install -r ${REQUIREMENTS}

COPY . .

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /usr/src/app/media /usr/src/app/staticfiles \
    && chown -R app:app /usr/src/app
USER app

EXPOSE 8000

# migrate + collectstatic تتم عند التشغيل (entrypoint) وليس أثناء البناء
ENTRYPOINT ["sh", "/usr/src/app/deploy/entrypoint.sh"]
CMD ["gunicorn", "book_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
