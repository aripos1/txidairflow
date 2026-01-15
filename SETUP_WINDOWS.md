# Windows에서 Airflow 설정 가이드

## 🚀 빠른 시작 (3단계)

### 1단계: Docker Desktop 설치

1. **Docker Desktop 다운로드**
   - https://www.docker.com/products/docker-desktop
   - "Download for Windows" 클릭

2. **설치**
   - 다운로드한 `.exe` 파일 실행
   - 설치 마법사 따라하기
   - 설치 완료 후 **컴퓨터 재시작** 필요

3. **Docker Desktop 실행**
   - 시작 메뉴에서 "Docker Desktop" 실행
   - 시스템 트레이에 Docker 아이콘 표시 확인
   - Docker Desktop이 완전히 시작될 때까지 대기 (몇 분 소요)

### 2단계: Docker 설치 확인

**PowerShell에서 확인:**

```powershell
# Docker 버전 확인
docker --version

# Docker Compose 버전 확인
docker compose version
```

**성공 시 출력 예시:**
```
Docker version 24.0.0, build abc123
Docker Compose version v2.20.0
```

### 3단계: Airflow 시작

```powershell
# airflow 폴더로 이동
cd airflow

# Airflow 시작 (백그라운드)
docker compose up -d

# 컨테이너 상태 확인
docker compose ps
```

**예상 출력:**
```
NAME                         STATUS
airflow-airflow-init-1       Exited (0)
airflow-airflow-scheduler-1  Up
airflow-airflow-webserver-1  Up
airflow-postgres-1           Up
```

### 4단계: 웹 UI 접속

1. 브라우저에서 `http://localhost:8080` 접속
2. 로그인:
   - 사용자명: `airflow`
   - 비밀번호: `airflow`

### 5단계: DAG 활성화 및 실행

1. DAG 목록에서 `bithumb_faq_crawler` 찾기
2. 왼쪽 토글 스위치를 **ON**으로 변경
3. DAG 이름 클릭하여 상세 페이지로 이동
4. 오른쪽 상단 **"Play" 버튼** → **"Trigger DAG"** 클릭

## ✅ 확인 사항

### 컨테이너가 정상 실행 중인지 확인

```powershell
docker compose ps
```

모든 컨테이너가 "Up" 상태여야 합니다.

### 로그 확인

```powershell
# 스케줄러 로그
docker compose logs scheduler

# 웹서버 로그
docker compose logs webserver

# 실시간 로그 확인
docker compose logs -f scheduler
```

### DAG가 보이지 않는 경우

```powershell
# DAG 파일 확인
ls airflow/dags/bithumb_faq_crawler.py

# Airflow가 DAG를 인식하는지 확인
docker compose exec scheduler airflow dags list
```

## 🛑 중지 및 재시작

### Airflow 중지

```powershell
cd airflow
docker compose down
```

### Airflow 재시작

```powershell
cd airflow
docker compose restart
```

### 완전히 제거 후 재시작

```powershell
cd airflow
docker compose down -v  # 볼륨까지 삭제
docker compose up -d
```

## 🐛 문제 해결

### 문제 1: "docker: command not found"

**해결:**
- Docker Desktop이 실행 중인지 확인
- PowerShell을 재시작
- Docker Desktop을 재시작

### 문제 2: "port 8080 is already in use"

**해결:**
```powershell
# 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8080

# 또는 docker-compose.yml에서 포트 변경
# ports:
#   - "8081:8080"  # 8081로 변경
```

### 문제 3: "WSL 2 installation is incomplete"

**해결:**
1. WSL 2 설치: https://docs.microsoft.com/windows/wsl/install
2. Docker Desktop 설정에서 "Use WSL 2 based engine" 활성화

### 문제 4: 컨테이너가 계속 재시작됨

**해결:**
```powershell
# 로그 확인
docker compose logs scheduler

# 환경 변수 확인
docker compose exec scheduler env | grep MONGODB
```

## 📝 환경 변수 확인

Airflow가 환경 변수를 올바르게 로드하는지 확인:

```powershell
# 프로젝트 루트의 .env 파일 확인
cat .env

# 또는 airflow 폴더의 .env 파일 확인
cat airflow/.env
```

필수 환경 변수:
- `MONGODB_URI`
- `MONGODB_DATABASE`
- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL` (선택사항)

## 🎯 빠른 테스트 명령어

```powershell
# 1. Airflow 시작
cd airflow
docker compose up -d

# 2. DAG 목록 확인
docker compose exec scheduler airflow dags list

# 3. 특정 DAG 테스트
docker compose exec scheduler airflow dags test bithumb_faq_crawler 2024-01-15

# 4. 특정 태스크 테스트
docker compose exec scheduler airflow tasks test bithumb_faq_crawler crawl_bithumb_faq 2024-01-15

# 5. 로그 확인
docker compose logs -f scheduler
```

## 💡 팁

- **첫 실행 시 시간이 걸립니다** (이미지 다운로드, 초기화 등)
- **컨테이너가 완전히 시작될 때까지 기다리세요** (약 1-2분)
- **웹 UI가 로드되지 않으면** 스케줄러 로그를 확인하세요
- **DAG가 보이지 않으면** DAG 파일에 문법 오류가 있을 수 있습니다
