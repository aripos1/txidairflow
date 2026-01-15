# 빗썸 FAQ 크롤링 Airflow 설정

이 디렉토리는 Apache Airflow를 사용하여 **자동으로** 빗썸 FAQ를 정기적으로 크롤링하고 MongoDB Atlas에 저장하는 설정을 포함합니다.

## 🎯 Airflow를 사용하는 이유

**Airflow의 핵심 가치는 자동화입니다!**

- ✅ **자동 실행**: 매일 지정된 시간에 자동으로 크롤링 실행
- ✅ **수동 작업 불필요**: 한 번 설정하면 계속 자동으로 실행됨
- ✅ **실패 시 자동 재시도**: 오류 발생 시 자동으로 재시도 (최대 2회)
- ✅ **작업 모니터링**: 웹 UI에서 실행 상태를 실시간으로 확인
- ✅ **로그 관리**: 모든 실행 기록과 로그를 자동으로 저장

**수동으로 크롤링할 필요가 없습니다!** Airflow가 모든 것을 자동으로 처리합니다.

## 구조

```
airflow/
├── dags/                    # Airflow DAG 파일들
│   ├── __init__.py
│   └── bithumb_faq_crawler.py  # 빗썸 FAQ 크롤링 DAG
├── config/                  # Airflow 설정 파일
│   └── airflow.cfg.example
├── Dockerfile               # Airflow Docker 이미지
├── docker-compose.yml       # Airflow Docker Compose 설정
└── README.md               # 이 파일
```

## 설정 방법

### 1. 환경 변수 설정

프로젝트 루트의 `.env` 파일에 다음 환경 변수가 설정되어 있어야 합니다:

```bash
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=chatbot_db
OPENAI_API_KEY=your_openai_api_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### 2. Docker Compose로 Airflow 실행

```bash
cd airflow
docker-compose up -d
```

### 3. Airflow 웹 UI 접속

브라우저에서 `http://localhost:8080` 접속
- 사용자명: `airflow`
- 비밀번호: `airflow` (docker-compose.yml에서 설정)

### 4. DAG 활성화 (한 번만!)

Airflow 웹 UI에서 `bithumb_faq_crawler` DAG를 찾아 **활성화**합니다.

**이것만 하면 끝입니다!** 이후로는 자동으로 실행됩니다.

## ⏰ 자동 실행 스케줄

- **기본 스케줄**: 매일 오전 2시 자동 실행 (`0 2 * * *`)
- 스케줄 변경: `airflow/dags/bithumb_faq_crawler.py` 파일의 `schedule_interval` 수정
- 예시:
  - 매일 오전 2시: `'0 2 * * *'`
  - 매일 오전 3시: `'0 3 * * *'`
  - 매주 월요일 오전 2시: `'0 2 * * 1'`
  - 매 6시간마다: `'0 */6 * * *'`

## 🔍 실행 상태 확인

### 웹 UI에서 확인 (권장)

1. `http://localhost:8080` 접속
2. `bithumb_faq_crawler` DAG 클릭
3. **Graph View**: 작업 실행 흐름 확인
4. **Tree View**: 과거 실행 기록 확인
5. **Logs**: 각 실행의 상세 로그 확인

### 명령줄에서 확인

```bash
# 실행 중인 DAG 목록 확인
docker-compose exec airflow-webserver airflow dags list

# 특정 DAG의 실행 상태 확인
docker-compose exec airflow-webserver airflow dags state bithumb_faq_crawler
```

## 🧪 수동 실행 (테스트/디버깅용)

**일반적으로는 필요 없습니다!** 하지만 테스트나 디버깅이 필요한 경우:

### 웹 UI에서:
1. DAG 선택
2. "Trigger DAG" 버튼 클릭

### 명령줄에서:
```bash
docker-compose exec airflow-webserver airflow dags trigger bithumb_faq_crawler
```

## 로그 확인

```bash
# 웹 서버 로그
docker-compose logs -f airflow-webserver

# 스케줄러 로그
docker-compose logs -f airflow-scheduler

# 특정 작업 로그는 Airflow 웹 UI에서 확인 가능
```

## 💡 자주 묻는 질문

### Q: 수동으로 크롤링해야 하나요?
**A: 아닙니다!** Airflow가 자동으로 실행합니다. DAG를 활성화한 후에는 아무것도 할 필요가 없습니다.

### Q: 언제 실행되나요?
**A: 매일 오전 2시에 자동 실행됩니다.** 스케줄은 `bithumb_faq_crawler.py`에서 변경할 수 있습니다.

### Q: 실행이 실패하면 어떻게 되나요?
**A: 자동으로 최대 2회 재시도합니다.** 그래도 실패하면 웹 UI에서 로그를 확인하여 문제를 해결할 수 있습니다.

### Q: 실행 기록은 어디서 확인하나요?
**A: Airflow 웹 UI (`http://localhost:8080`)에서 확인할 수 있습니다.** 모든 실행 기록과 로그가 저장됩니다.

## 문제 해결

### MongoDB 연결 실패
- `.env` 파일의 `MONGODB_URI`가 올바른지 확인
- MongoDB Atlas 네트워크 접근 설정 확인 (IP 화이트리스트)

### 크롤링 실패
- 인터넷 연결 확인
- 빗썸 웹사이트 접근 가능 여부 확인
- Airflow 로그에서 상세 오류 메시지 확인

### DAG가 보이지 않음
- `airflow/dags/` 디렉토리에 DAG 파일이 있는지 확인
- DAG 파일에 문법 오류가 없는지 확인
- Airflow 스케줄러가 실행 중인지 확인

## 참고

- [Apache Airflow 공식 문서](https://airflow.apache.org/docs/)
- [Airflow Docker Compose 가이드](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html)
