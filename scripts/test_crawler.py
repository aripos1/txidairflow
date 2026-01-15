"""
Airflow 크롤링 테스트 스크립트
로컬에서 크롤링 기능을 테스트할 수 있습니다.
"""
import asyncio
import sys
import os
from pathlib import Path

# Python 버전 확인
print(f"Python 버전: {sys.version}")
print(f"Python 실행 경로: {sys.executable}")

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
    print(f"[OK] 프로젝트 루트 .env 파일 로드 완료: {project_env}")
    env_loaded = True

if airflow_env.exists():
    load_dotenv(airflow_env, override=True)  # airflow/.env가 우선순위 높음
    print(f"[OK] airflow/.env 파일 로드 완료: {airflow_env}")
    env_loaded = True

if not env_loaded:
    print("[WARNING] .env 파일을 찾을 수 없습니다.")
    print(f"      확인한 경로:")
    print(f"      1. {project_env}")
    print(f"      2. {airflow_env}")

# 필수 환경 변수 확인
import os
required_vars = ["MONGODB_URI", "OPENAI_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"\n[ERROR] 필수 환경 변수가 설정되지 않았습니다:")
    for var in missing_vars:
        print(f"  - {var}")
    print("\n[INFO] .env 파일에 다음을 설정하세요:")
    print("  MONGODB_URI=your_mongodb_uri")
    print("  OPENAI_API_KEY=your_openai_api_key")
    print("  MONGODB_DATABASE=chatbot_db")
    print("  OPENAI_EMBEDDING_MODEL=text-embedding-3-small")
    sys.exit(1)

# Airflow scripts 경로 추가
airflow_dir = Path(__file__).parent.parent
sys.path.insert(0, str(airflow_dir))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Playwright 설치 확인
print("\n[CHECK] Playwright 설치 확인 중...")
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_INSTALLED = True
    print("[OK] Playwright 설치 확인됨")
except ImportError as e:
    PLAYWRIGHT_INSTALLED = False
    print("[ERROR] Playwright가 설치되지 않았습니다.")
    print(f"   오류: {e}")
    print("\n[INFO] 설치 방법:")
    print(f"   1. {sys.executable} -m pip install playwright")
    print(f"   2. {sys.executable} -m playwright install chromium")
    print("\n[INFO] 현재 사용 중인 Python에 Playwright를 설치해야 합니다.")
    sys.exit(1)

# bithumb_crawler 모듈 import
print("[CHECK] 크롤링 모듈 로드 중...")
try:
    from airflow.scripts.bithumb_crawler import crawl_bithumb_faq
    print("[OK] 크롤링 모듈 로드 완료")
except Exception as e:
    print(f"[ERROR] 크롤링 모듈 로드 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


async def test_crawler(limit: int = 3):
    """크롤링 테스트 (제한된 수의 아티클만)"""
    print("\n" + "=" * 60)
    print("빗썸 FAQ 크롤링 테스트")
    print("=" * 60)
    print(f"테스트 모드: 최대 {limit}개 아티클만 크롤링합니다.")
    print("=" * 60)
    
    try:
        await crawl_bithumb_faq(limit=limit, headless=True)
        print("\n[SUCCESS] 테스트 완료!")
        return True
    except Exception as e:
        print(f"\n[FAILED] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='빗썸 FAQ 크롤링 테스트')
    parser.add_argument('--limit', type=int, default=3, help='크롤링할 아티클 수 (기본값: 3)')
    parser.add_argument('--no-headless', action='store_true', help='헤드리스 모드 비활성화 (브라우저 표시)')
    
    args = parser.parse_args()
    
    # 테스트 실행
    result = asyncio.run(test_crawler(limit=args.limit))
    
    if result:
        print("\n[INFO] 전체 크롤링을 실행하려면:")
        print("   python scripts/test_crawler.py --limit 0  # 0은 제한 없음")
        sys.exit(0)
    else:
        sys.exit(1)
