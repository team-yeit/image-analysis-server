FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# best.pt 파일 존재 및 크기 확인 (LFS 포인터가 아닌 실제 파일인지)
RUN if [ ! -f best.pt ]; then \
        echo "ERROR: best.pt not found!"; \
        exit 1; \
    fi && \
    FILE_SIZE=$(stat -f%z best.pt 2>/dev/null || stat -c%s best.pt 2>/dev/null) && \
    if [ "$FILE_SIZE" -lt 1000000 ]; then \
        echo "ERROR: best.pt is too small ($FILE_SIZE bytes). It might be a Git LFS pointer file."; \
        echo "Run 'git lfs pull' before building the Docker image."; \
        exit 1; \
    fi && \
    echo "✓ best.pt found ($(echo $FILE_SIZE | awk '{print int($1/1024/1024)}')MB)"

RUN mkdir -p /app/media/uploads /app/results /app/staticfiles
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/', timeout=5)" || exit 1

CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]