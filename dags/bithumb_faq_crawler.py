"""
빗썸 FAQ 크롤링 Airflow DAG
매일 자동으로 빗썸 고객지원 센터 FAQ를 크롤링하여 MongoDB Atlas에 저장합니다.
app/scripts/data/crawl_bithumb_playwright.py를 사용합니다.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
# Airflow 컨테이너에서는 /opt/airflow/project로 마운트됨
project_root = Path('/opt/airflow/project')
if not project_root.exists():
    # 로컬 개발 환경에서는 상대 경로 사용
    project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
from dotenv import load_dotenv

# 1. 프로젝트 루트의 .env 파일 확인
project_env = project_root / '.env'
# 2. airflow 폴더의 .env 파일 확인
airflow_dir = Path(__file__).parent.parent
airflow_env = airflow_dir / '.env'

# 프로젝트 루트 .env 먼저 로드
if project_env.exists():
    load_dotenv(project_env)

# airflow/.env 파일이 있으면 우선순위로 로드 (override=True)
if airflow_env.exists():
    load_dotenv(airflow_env, override=True)

default_args = {
    'owner': 'bithumb-crawler',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
}

dag = DAG(
    'bithumb_faq_crawler',
    default_args=default_args,
    description='빗썸 FAQ 크롤링 및 MongoDB Atlas 저장 (Playwright 사용)',
    schedule_interval='0 2 * * *',  # 매일 오전 2시 실행
    catchup=False,
    tags=['bithumb', 'crawler', 'faq', 'mongodb', 'playwright'],
    max_active_runs=1,  # 동시 실행 방지
)


def check_playwright_installation(**context):
    """Playwright 설치 확인"""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("Playwright 설치 확인 시작...")
    
    try:
        from playwright.async_api import async_playwright
        logger.info("✅ Playwright Python 패키지 설치 확인됨")
        return True
    except ImportError:
        error_msg = "Playwright가 설치되지 않았습니다. requirements.txt에 playwright가 포함되어 있는지 확인하세요."
        logger.error(f"❌ {error_msg}")
        raise ImportError(error_msg)


def check_mongodb_connection(**context):
    """MongoDB 연결 상태 확인 (Airflow 전용 모듈 사용)"""
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("MongoDB 연결 확인 시작...")
    
    # Airflow 전용 모듈 사용 (app과 완전히 분리)
    from airflow.scripts.mongodb_store import AirflowVectorStore
    
    async def _check():
        vector_store = AirflowVectorStore()
        connected = await vector_store.connect()
        if connected:
            logger.info("✅ MongoDB 연결 성공")
            await vector_store.disconnect()
            return True
        else:
            logger.error("❌ MongoDB 연결 실패")
            return False
    
    try:
        result = asyncio.run(_check())
        if not result:
            raise Exception("MongoDB 연결 실패 - 환경 변수(MONGODB_URI, MONGODB_DATABASE)를 확인하세요")
        return result
    except Exception as e:
        logger.error(f"MongoDB 연결 확인 중 오류: {e}")
        raise


def run_crawl_bithumb_faq(**context):
    """빗썸 FAQ 크롤링 실행 (Airflow 전용 모듈 사용)"""
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("빗썸 FAQ 크롤링 시작 (Playwright 사용)")
    logger.info("=" * 60)
    
    # Airflow 전용 크롤링 모듈 사용 (app과 완전히 분리)
    from airflow.scripts.bithumb_crawler import crawl_bithumb_faq
    
    try:
        # Playwright 사용 크롤링 실행 (헤드리스 모드)
        # limit=None으로 설정하면 모든 아티클 크롤링
        asyncio.run(crawl_bithumb_faq(limit=None, headless=True))
        logger.info("✅ 빗썸 FAQ 크롤링 완료")
        
        # Airflow XCom에 성공 정보 저장
        context['ti'].xcom_push(key='crawl_status', value='success')
        context['ti'].xcom_push(key='crawl_method', value='playwright')
        return 'success'
        
    except Exception as e:
        logger.error(f"❌ 빗썸 FAQ 크롤링 실패: {e}")
        logger.exception("상세 오류 정보:")
        
        # Airflow XCom에 실패 정보 저장
        context['ti'].xcom_push(key='crawl_status', value='failed')
        context['ti'].xcom_push(key='crawl_error', value=str(e))
        context['ti'].xcom_push(key='crawl_method', value='playwright')
        raise


def verify_mongodb_data(**context):
    """MongoDB에 저장된 데이터 확인 (Airflow 전용 모듈 사용)"""
    import asyncio
    import logging
    from datetime import datetime, timedelta
    
    logger = logging.getLogger(__name__)
    logger.info("MongoDB 데이터 확인 시작...")
    
    # Airflow 전용 모듈 사용 (app과 완전히 분리)
    from airflow.scripts.mongodb_store import AirflowVectorStore
    
    ti = context['ti']
    
    async def _verify():
        vector_store = AirflowVectorStore()
        connected = await vector_store.connect()
        if not connected:
            logger.error("MongoDB 연결 실패")
            return None
        
        try:
            collection = vector_store.collection
            if collection is None:
                logger.error("MongoDB 컬렉션이 없습니다")
                return None
            
            # 최근 24시간 내 저장된 zendesk_article 타입 문서 수
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            count = await collection.count_documents({
                "metadata.type": "zendesk_article",
                "created_at": {"$gte": yesterday}
            })
            
            logger.info(f"✅ 최근 24시간 내 저장된 FAQ 문서 수: {count}개")
            
            # 전체 문서 수 확인
            total_count = await collection.count_documents({
                "metadata.type": "zendesk_article"
            })
            logger.info(f"📊 전체 FAQ 문서 수: {total_count}개")
            
            return {'count_24h': count, 'total': total_count}
            
        except Exception as e:
            logger.error(f"데이터 확인 중 오류: {e}")
            return None
        finally:
            await vector_store.disconnect()
    
    try:
        result = asyncio.run(_verify())
        if result:
            # XCom에 통계 저장
            ti.xcom_push(key='documents_count_24h', value=result['count_24h'])
            ti.xcom_push(key='documents_count_total', value=result['total'])
            return True
        else:
            logger.warning("⚠️ 데이터 확인 실패 (크롤링은 성공했을 수 있음)")
            return False
    except Exception as e:
        logger.error(f"데이터 확인 중 오류: {e}")
        return False


# 작업 정의
with TaskGroup("preparation", dag=dag) as prep_group:
    """준비 작업 그룹"""
    check_playwright = PythonOperator(
        task_id='check_playwright_installation',
        python_callable=check_playwright_installation,
        dag=dag,
    )
    
    check_mongodb = PythonOperator(
        task_id='check_mongodb_connection',
        python_callable=check_mongodb_connection,
        dag=dag,
    )
    
    # Playwright 확인 후 MongoDB 확인
    check_playwright >> check_mongodb

with TaskGroup("crawling", dag=dag) as crawl_group:
    """크롤링 작업 그룹"""
    crawl_task = PythonOperator(
        task_id='crawl_bithumb_faq',
        python_callable=run_crawl_bithumb_faq,
        dag=dag,
    )

with TaskGroup("verification", dag=dag) as verify_group:
    """검증 작업 그룹"""
    verify_data = PythonOperator(
        task_id='verify_mongodb_data',
        python_callable=verify_mongodb_data,
        dag=dag,
    )

# 작업 실행 순서 정의
prep_group >> crawl_group >> verify_group
