FROM apache/airflow:2.8.0

USER root

# 1. 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libxshmfence1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# 2. 파이썬 패키지 설치
# --constraint 옵션을 제거하여 openai 등의 최신 패키지 설치를 허용합니다.
RUN pip install --no-cache-dir \
    "playwright==1.40.0" \
    "apache-airflow-providers-postgres" \
    "psycopg2-binary" \
    "beautifulsoup4" \
    "lxml" \
    "motor" \
    "pymongo" \
    "openai" \
    "python-dotenv"

# 3. Playwright 시스템 의존성 설치 (ROOT 권한)
USER root
# PYTHONPATH를 명시하여 root가 airflow 패키지를 인식하고 실행할 수 있게 함
ENV PYTHONPATH="/home/airflow/.local/lib/python3.8/site-packages"
RUN /home/airflow/.local/bin/playwright install-deps chromium

# 4. 브라우저 바이너리 설치 (AIRFLOW 권한)
USER airflow
RUN playwright install chromium

WORKDIR /opt/airflow