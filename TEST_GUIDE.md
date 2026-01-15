# Airflow 테스트 가이드

## ⚠️ 사전 요구사항

### Docker 설치 확인

**Windows에서 Docker 설치:**
1. Docker Desktop for Windows 다운로드: https://www.docker.com/products/docker-desktop
2. 설치 후 Docker Desktop 실행
3. PowerShell에서 확인:
   ```powershell
   docker --version
   docker compose version
   ```

**Docker가 없는 경우:**
- 방법 3 (로컬 스크립트 테스트)를 사용하세요.

## 🧪 테스트 방법

### 방법 1: 웹 UI에서 수동 실행 (권장)

#### 1단계: Airflow 시작

**Windows PowerShell:**
```powershell
cd airflow
docker compose up -d
```

**참고:** 최신 Docker Desktop은 `docker-compose` 대신 `docker compose` (하이픈 없이)를 사용합니다.

#### 2단계: 웹 UI 접속

브라우저에서 `http://localhost:8080` 접속
- 사용자명: `airflow`
- 비밀번호: `airflow`

#### 3단계: DAG 활성화 및 실행

1. `bithumb_faq_crawler` DAG 찾기
2. 왼쪽 토글 스위치를 **ON**으로 변경 (DAG 활성화)
3. DAG 이름 클릭하여 상세 페이지로 이동
4. 오른쪽 상단의 **"Play" 버튼** 클릭
5. "Trigger DAG" 클릭하여 즉시 실행

#### 4단계: 실행 상태 확인

- **녹색**: 성공
- **빨간색**: 실패
- **파란색**: 실행 중
- **주황색**: 재시도 중

#### 5단계: 로그 확인

1. DAG 그래프에서 작업(태스크) 클릭
2. "Log" 버튼 클릭
3. 로그에서 다음을 확인:
   - 이미지 정보 발견 로그
   - 크롤링 진행 상황
   - MongoDB 저장 상태

### 방법 2: CLI로 직접 실행

**Windows PowerShell:**
```powershell
# Airflow 컨테이너 접속
docker exec -it airflow-airflow-webserver-1 bash

# 또는 스케줄러 컨테이너
docker exec -it airflow-airflow-scheduler-1 bash

# DAG 테스트 실행
airflow dags test bithumb_faq_crawler 2024-01-15

# 특정 태스크만 테스트
airflow tasks test bithumb_faq_crawler crawl_bithumb_faq 2024-01-15
```

### 방법 3: 로컬 스크립트로 테스트 (Airflow 없이) ⭐ Docker 불필요

**Windows PowerShell:**
```powershell
# 프로젝트 루트에서
python airflow/scripts/test_crawler.py --limit 3

# 또는 더 많은 아티클 테스트
python airflow/scripts/test_crawler.py --limit 10

# 전체 크롤링 (제한 없음)
python airflow/scripts/test_crawler.py --limit 0
```

**이 방법의 장점:**
- ✅ Docker 설치 불필요
- ✅ 빠른 테스트 가능
- ✅ 동일한 크롤링 로직 사용
- ✅ MongoDB 저장 확인 가능

## 🔍 테스트 체크리스트

### ✅ 크롤링 테스트

- [ ] Playwright 브라우저가 정상적으로 시작되는가?
- [ ] 아티클 URL이 정상적으로 발견되는가?
- [ ] 아티클 내용이 정상적으로 추출되는가?
- [ ] 이미지 정보가 정상적으로 추출되는가?

### ✅ 이미지 처리 테스트

- [ ] 이미지 URL이 정상적으로 추출되는가?
- [ ] 이미지 alt 텍스트가 추출되는가?
- [ ] 이미지 캡션이 추출되는가?
- [ ] 이미지 정보가 MongoDB에 저장되는가?

### ✅ 변경 감지 테스트

- [ ] 동일한 아티클을 다시 크롤링하면 "skipped" 상태가 되는가?
- [ ] 아티클 내용이 변경되면 "updated" 상태가 되는가?
- [ ] content_hash가 정상적으로 계산되는가?

### ✅ MongoDB 저장 테스트

- [ ] 임베딩이 정상적으로 생성되는가?
- [ ] 청크가 정상적으로 분할되는가?
- [ ] 모든 청크에 이미지 정보가 포함되는가?
- [ ] 메타데이터에 article_id, content_hash가 포함되는가?

## 📊 로그에서 확인할 항목

### 성공적인 크롤링 로그 예시

```
✅ MongoDB 연결 성공!
✅ 브라우저 시작 완료!
총 발견된 아티클 수: 150개
이미지 정보 발견: 3개 이미지 (아티클: 53957028253721)
✅ 신규 저장 완료: 열두번째, 잠들어 있는 '2,916억 원' 휴면 자산 찾기 캠페인...
⏭️  변경사항 없음 (스킵): ...
```

### 이미지 처리 로그 예시

```
이미지 정보 발견: 2개 이미지 (아티클: 53957028253721)
FAQ 1에 이미지 2개 발견 - 프롬프트에 포함
```

## 🐛 문제 해결

### 문제: DAG가 보이지 않음

```bash
# DAG 파일이 올바른 위치에 있는지 확인
ls airflow/dags/bithumb_faq_crawler.py

# Airflow 로그 확인
docker logs airflow-airflow-scheduler-1
```

### 문제: 환경 변수가 로드되지 않음

```bash
# .env 파일 확인
cat airflow/.env
# 또는
cat .env

# 환경 변수가 설정되어 있는지 확인
docker exec airflow-airflow-webserver-1 env | grep MONGODB
```

### 문제: Playwright 브라우저 실행 실패

```bash
# Playwright 설치 확인
docker exec airflow-airflow-webserver-1 playwright --version

# 브라우저 설치 확인
docker exec airflow-airflow-webserver-1 playwright install chromium
```

### 문제: MongoDB 연결 실패

```bash
# MongoDB URI 확인
docker exec airflow-airflow-webserver-1 env | grep MONGODB_URI

# 연결 테스트
docker exec airflow-airflow-webserver-1 python -c "
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from dotenv import load_dotenv
load_dotenv('/opt/airflow/project/.env')
client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
asyncio.run(client.admin.command('ping'))
print('MongoDB 연결 성공!')
"
```

## 🎯 빠른 테스트 명령어

### Docker 사용 시 (방법 1)

**Windows PowerShell:**
```powershell
# 1. Airflow 시작
cd airflow
docker compose up -d

# 2. 로그 확인 (별도 터미널)
docker logs -f airflow-airflow-scheduler-1

# 3. 웹 UI 접속
# http://localhost:8080 (airflow/airflow)

# 4. DAG 활성화 후 수동 실행
# 웹 UI에서 "Trigger DAG" 클릭

# 5. MongoDB 데이터 확인
python airflow/scripts/check_mongodb_data.py
```

### Docker 없이 테스트 (방법 3) ⭐

**Windows PowerShell:**
```powershell
# 1. 크롤링 테스트 (3개 아티클만)
python airflow/scripts/test_crawler.py --limit 3

# 2. MongoDB 데이터 확인
python airflow/scripts/check_mongodb_data.py
```

## 📝 테스트 시나리오

### 시나리오 1: 신규 크롤링

1. MongoDB에서 기존 데이터 삭제 (선택사항)
2. DAG 실행
3. "created" 상태의 아티클 확인
4. 이미지 정보가 포함되었는지 확인

### 시나리오 2: 변경 감지

1. 이미 크롤링된 아티클이 있는 상태에서 DAG 실행
2. "skipped" 상태 확인 (내용 변경 없음)
3. 웹사이트에서 아티클 내용 수정
4. DAG 재실행
5. "updated" 상태 확인

### 시나리오 3: 이미지 포함 아티클

1. 이미지가 포함된 아티클 URL 확인
   - 예: `https://support.bithumb.com/hc/ko/articles/53957028253721`
2. 해당 아티클 크롤링
3. 로그에서 "이미지 정보 발견" 확인
4. MongoDB에서 이미지 정보 확인
