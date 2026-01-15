"""
MongoDB에 저장된 데이터 확인 스크립트
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
from dotenv import load_dotenv

# 1. 프로젝트 루트의 .env 파일 확인
project_env = project_root / '.env'
# 2. airflow 폴더의 .env 파일 확인
airflow_dir = Path(__file__).parent.parent
airflow_env = airflow_dir / '.env'

env_loaded = False
if project_env.exists():
    load_dotenv(project_env)
    env_loaded = True

if airflow_env.exists():
    load_dotenv(airflow_env, override=True)
    env_loaded = True

if not env_loaded:
    print("[WARNING] .env 파일을 찾을 수 없습니다.")

# Airflow scripts 경로 추가
sys.path.insert(0, str(airflow_dir))

from airflow.scripts.mongodb_store import AirflowVectorStore


async def check_mongodb_data():
    """MongoDB에 저장된 데이터 확인"""
    print("=" * 60)
    print("MongoDB 데이터 확인")
    print("=" * 60)
    
    vector_store = AirflowVectorStore()
    connected = await vector_store.connect()
    
    if not connected:
        print("[ERROR] MongoDB 연결 실패")
        return
    
    try:
        collection = vector_store.collection
        if collection is None:
            print("[ERROR] MongoDB 컬렉션이 없습니다")
            return
        
        # 전체 FAQ 문서 수
        total_count = await collection.count_documents({
            "metadata.type": "zendesk_article"
        })
        print(f"\n[전체 FAQ 문서 수] {total_count}개")
        
        # 최근 24시간 내 저장된 문서 수
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_count = await collection.count_documents({
            "metadata.type": "zendesk_article",
            "created_at": {"$gte": yesterday}
        })
        print(f"[최근 24시간 내 저장된 문서 수] {recent_count}개")
        
        # 최근 저장된 문서 5개 조회
        print("\n[최근 저장된 문서 5개]")
        print("-" * 60)
        
        recent_docs = await collection.find({
            "metadata.type": "zendesk_article"
        }).sort("created_at", -1).limit(5).to_list(length=5)
        
        for i, doc in enumerate(recent_docs, 1):
            metadata = doc.get("metadata", {})
            article_id = metadata.get("article_id", "N/A")
            title = metadata.get("title", "N/A")
            url = metadata.get("url", "N/A")
            created_at = doc.get("created_at", "N/A")
            
            if isinstance(created_at, datetime):
                created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                created_at_str = str(created_at)
            
            print(f"\n{i}. 아티클 ID: {article_id}")
            print(f"   제목: {title[:50]}..." if len(title) > 50 else f"   제목: {title}")
            print(f"   URL: {url}")
            print(f"   저장 시간: {created_at_str}")
        
        print("\n" + "=" * 60)
        print("[SUCCESS] 데이터 확인 완료")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] 데이터 확인 중 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await vector_store.disconnect()


if __name__ == "__main__":
    asyncio.run(check_mongodb_data())
