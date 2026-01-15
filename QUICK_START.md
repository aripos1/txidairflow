# Airflow 빠른 시작 가이드

## ⚠️ 사전 요구사항

**Docker Desktop이 설치되어 있어야 합니다.**
- 설치 방법: `airflow/SETUP_WINDOWS.md` 참고
- 확인: `docker --version` 명령어로 확인

## 🚀 5분 안에 시작하기

### 1단계: Airflow 시작

**Windows PowerShell:**
```powershell
cd airflow
docker compose up -d
```

**참고:** 최신 Docker는 `docker-compose` 대신 `docker compose` (하이픈 없이)를 사용합니다.

### 2단계: 웹 UI 접속

브라우저에서 `http://localhost:8080` 접속
- 사용자명: `airflow`
- 비밀번호: `airflow`

### 3단계: DAG 활성화

1. `bithumb_faq_crawler` DAG 찾기
2. 왼쪽 토글 스위치를 **ON**으로 변경

**끝!** 이제 매일 오전 2시에 자동으로 크롤링이 실행됩니다.

## ✅ 확인 방법

### 실행 상태 확인

웹 UI에서:
- 초록색 = 성공
- 빨간색 = 실패
- 파란색 = 실행 중

### 로그 확인

1. DAG 클릭
2. 최근 실행 클릭
3. 작업 클릭
4. "Log" 버튼 클릭

## 🎯 핵심 포인트

- **한 번만 설정하면 자동으로 실행됩니다**
- **수동 작업이 필요 없습니다**
- **실패 시 자동 재시도됩니다**
- **모든 실행 기록이 저장됩니다**

## 📅 스케줄 변경

`airflow/dags/bithumb_faq_crawler.py` 파일에서:

```python
schedule_interval='0 2 * * *',  # 매일 오전 2시
```

다음과 같이 변경 가능:
- `'0 3 * * *'` - 매일 오전 3시
- `'0 */6 * * *'` - 매 6시간마다
- `'0 2 * * 1'` - 매주 월요일 오전 2시

## 🛑 중지 방법

```bash
cd airflow
docker-compose down
```

## 🔄 재시작 방법

```bash
cd airflow
docker-compose restart
```
