#!/bin/bash
# Airflow 커스텀 엔트리포인트
# 프로젝트 requirements.txt를 설치한 후 Airflow 실행

set -e

# 프로젝트 requirements.txt가 있으면 설치
if [ -f /opt/airflow/project/requirements.txt ]; then
    echo "Installing project requirements..."
    pip install --no-cache-dir -r /opt/airflow/project/requirements.txt || echo "Warning: Failed to install some requirements"
fi

# Playwright 브라우저 설치 (requirements.txt에 playwright가 포함된 경우)
if command -v playwright &> /dev/null || python -c "import playwright" 2>/dev/null; then
    echo "Installing Playwright browsers..."
    playwright install chromium || echo "Warning: Failed to install Playwright browsers"
    # 시스템 의존성 설치 (이미 Dockerfile에서 설치했지만 확인)
    playwright install-deps chromium || echo "Warning: Failed to install Playwright system dependencies"
fi

# 원본 Airflow 엔트리포인트 실행 (우선순위: /entrypoint > /usr/local/bin/entrypoint)
if [ -f /entrypoint ]; then
    exec /entrypoint "$@"
elif [ -f /usr/local/bin/entrypoint ]; then
    exec /usr/local/bin/entrypoint "$@"
else
    # entrypoint를 찾을 수 없으면 직접 airflow 실행
    exec /home/airflow/.local/bin/airflow "$@"
fi
