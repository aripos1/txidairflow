"""
Airflow 전용 빗썸 FAQ 크롤링 모듈
Playwright를 사용하여 Cloudflare 보호를 우회합니다.
app과 완전히 분리된 독립적인 모듈
"""
import asyncio
import logging
from typing import List, Dict, Optional, Set, TYPE_CHECKING
import re
from bs4 import BeautifulSoup
from datetime import datetime

# Playwright 설정
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # 타입 힌트를 위한 더미 클래스
    if TYPE_CHECKING:
        from playwright.async_api import Page
    else:
        # 런타임에서는 Any 타입 사용
        from typing import Any
        Page = Any  # type: ignore
    logging.warning("Playwright가 설치되지 않았습니다. 크롤링 기능을 사용할 수 없습니다.")

# Zendesk Help Center 설정
BASE_URL = "https://support.bithumb.com"
LOCALE = "ko"
HELP_CENTER_BASE = f"{BASE_URL}/hc/{LOCALE}"

logger = logging.getLogger(__name__)


def extract_images_from_element(soup: BeautifulSoup) -> List[Dict]:
    """요소에서 이미지 정보 추출"""
    images = []
    
    if not soup:
        return images
    
    img_tags = soup.find_all('img')
    
    for img in img_tags:
        img_info = {}
        
        # 이미지 URL 추출
        img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
        if img_url:
            if img_url.startswith('//'):
                img_url = f"https:{img_url}"
            elif img_url.startswith('/'):
                img_url = f"{BASE_URL}{img_url}"
            elif not img_url.startswith('http'):
                continue
            
            img_info['url'] = img_url
        
        # Alt 텍스트 추출
        alt_text = img.get('alt', '').strip()
        if alt_text:
            img_info['alt'] = alt_text
        
        # Title 속성 추출
        title_text = img.get('title', '').strip()
        if title_text:
            img_info['title'] = title_text
        
        # 이미지 주변 텍스트 추출
        parent = img.find_parent(['figure', 'div', 'p'])
        if parent:
            caption = parent.find(class_=re.compile(r'caption|figcaption|image.*caption', re.I))
            if caption:
                caption_text = caption.get_text(strip=True)
                if caption_text:
                    img_info['caption'] = caption_text
            
            img_text_parts = []
            prev_sibling = img.find_previous_sibling(['p', 'div', 'span'])
            if prev_sibling:
                prev_text = prev_sibling.get_text(strip=True)
                if prev_text and len(prev_text) < 200:
                    img_text_parts.append(prev_text)
            
            next_sibling = img.find_next_sibling(['p', 'div', 'span'])
            if next_sibling:
                next_text = next_sibling.get_text(strip=True)
                if next_text and len(next_text) < 200:
                    img_text_parts.append(next_text)
            
            if img_text_parts:
                img_info['context'] = ' '.join(img_text_parts)
        
        if img_info:
            images.append(img_info)
    
    return images


async def discover_all_articles(page, limit: Optional[int] = None) -> List[str]:
    """모든 아티클 URL 발견"""
    all_articles = set()
    
    try:
        logger.info("메인 페이지 접속 중...")
        await page.goto(f"{HELP_CENTER_BASE}", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        page_source = await page.content()
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 카테고리 링크 찾기
        category_links = soup.find_all('a', href=re.compile(r'/hc/' + LOCALE + r'/categories/\d+'))
        categories = set()
        for link in category_links:
            href = link.get('href', '')
            if href:
                if href.startswith('/'):
                    full_url = f"{BASE_URL}{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue
                if '/categories/' in full_url:
                    categories.add(full_url)
        
        logger.info(f"발견된 카테고리 수: {len(categories)}")
        
        # 각 카테고리에서 섹션 찾기
        all_sections = set()
        for category_url in categories:
            try:
                logger.info(f"카테고리 접속: {category_url}")
                await page.goto(category_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(1)
                
                cat_soup = BeautifulSoup(await page.content(), 'html.parser')
                section_links = cat_soup.find_all('a', href=re.compile(r'/hc/' + LOCALE + r'/sections/\d+'))
                
                for link in section_links:
                    href = link.get('href', '')
                    if href:
                        if href.startswith('/'):
                            full_url = f"{BASE_URL}{href}"
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            continue
                        if '/sections/' in full_url:
                            all_sections.add(full_url)
            except Exception as e:
                logger.warning(f"카테고리 처리 실패 ({category_url}): {e}")
                continue
        
        logger.info(f"발견된 섹션 수: {len(all_sections)}")
        
        # 각 섹션에서 아티클 찾기
        for section_url in all_sections:
            try:
                logger.info(f"섹션 접속: {section_url}")
                await page.goto(section_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(1)
                
                section_soup = BeautifulSoup(await page.content(), 'html.parser')
                article_links = section_soup.find_all('a', href=re.compile(r'/hc/' + LOCALE + r'/articles/\d+'))
                
                for link in article_links:
                    href = link.get('href', '')
                    if href:
                        if href.startswith('/'):
                            full_url = f"{BASE_URL}{href}"
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            continue
                        if '/articles/' in full_url:
                            all_articles.add(full_url)
                            
                        if limit and len(all_articles) >= limit:
                            break
                
                if limit and len(all_articles) >= limit:
                    break
            except Exception as e:
                logger.warning(f"섹션 처리 실패 ({section_url}): {e}")
                continue
        
        # 메인 페이지에서도 직접 아티클 링크 찾기
        await page.goto(f"{HELP_CENTER_BASE}", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(1)
        main_soup = BeautifulSoup(await page.content(), 'html.parser')
        main_article_links = main_soup.find_all('a', href=re.compile(r'/hc/' + LOCALE + r'/articles/\d+'))
        for link in main_article_links:
            href = link.get('href', '')
            if href:
                if href.startswith('/'):
                    full_url = f"{BASE_URL}{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue
                if '/articles/' in full_url:
                    all_articles.add(full_url)
        
        logger.info(f"총 발견된 아티클 수: {len(all_articles)}")
        return list(all_articles)
        
    except Exception as e:
        logger.error(f"아티클 발견 실패: {e}")
        return []


async def extract_article_content(page, article_url: str) -> Optional[Dict]:
    """아티클 내용 추출"""
    try:
        logger.info(f"아티클 접속: {article_url}")
        await page.goto(article_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(1)
        
        page_source = await page.content()
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 제목 추출
        title_elem = soup.find('h1') or soup.find(class_=re.compile(r'article.*title|title.*article', re.I))
        title = title_elem.get_text(strip=True) if title_elem else "제목 없음"
        
        # 섹션/카테고리 정보 추출
        section_name = None
        category_name = None
        
        # Breadcrumb에서 섹션/카테고리 정보 추출
        breadcrumb = soup.find(class_=re.compile(r'breadcrumb|bread.*crumb', re.I))
        if breadcrumb:
            breadcrumb_links = breadcrumb.find_all('a')
            for link in breadcrumb_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if '/sections/' in href and not section_name:
                    section_name = text
                elif '/categories/' in href and not category_name:
                    category_name = text
        
        # 본문 추출
        body_elem = (
            soup.find(class_=re.compile(r'article.*body|body.*article', re.I)) or
            soup.find('article') or
            soup.find(id=re.compile(r'article.*content|content.*article', re.I))
        )
        
        images = []
        body_text = ""
        
        if body_elem:
            images = extract_images_from_element(body_elem)
            for tag in body_elem(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            body_text = body_elem.get_text(separator='\n', strip=True)
        else:
            main_content = soup.find('main') or soup.find('div', class_=re.compile(r'content|main', re.I))
            if main_content:
                images = extract_images_from_element(main_content)
                for tag in main_content(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    tag.decompose()
                body_text = main_content.get_text(separator='\n', strip=True)
            else:
                images = extract_images_from_element(soup)
                body_text = soup.get_text(separator='\n', strip=True)
        
        # 텍스트 정리
        lines = [line.strip() for line in body_text.split('\n') if line.strip()]
        clean_body = '\n'.join(lines)
        
        # 이미지 설명 추가
        image_descriptions = []
        for img in images:
            img_desc_parts = []
            if img.get('alt'):
                img_desc_parts.append(f"[이미지 설명: {img['alt']}]")
            if img.get('caption'):
                img_desc_parts.append(f"[이미지 캡션: {img['caption']}]")
            if img.get('context'):
                img_desc_parts.append(f"[이미지 주변 설명: {img['context']}]")
            if img_desc_parts:
                image_descriptions.append(' '.join(img_desc_parts))
        
        if image_descriptions:
            clean_body += "\n\n" + "\n".join(image_descriptions)
        
        # 아티클 ID 추출
        article_id_match = re.search(r'/articles/(\d+)', article_url)
        article_id = article_id_match.group(1) if article_id_match else None
        
        return {
            "url": article_url,
            "title": title,
            "body": clean_body,
            "article_id": article_id,
            "images": images,
            "section_name": section_name,
            "category_name": category_name,
            "full_text": f"제목: {title}\n\n{clean_body}"
        }
        
    except Exception as e:
        logger.error(f"아티클 내용 추출 실패 ({article_url}): {e}")
        return None


async def crawl_bithumb_faq(limit: Optional[int] = None, headless: bool = True):
    """빗썸 FAQ 크롤링 메인 함수"""
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError("Playwright가 설치되지 않았습니다.")
    
    # 상대 경로 import (airflow/scripts 내부)
    from .mongodb_store import AirflowVectorStore
    
    logger.info("=" * 60)
    logger.info("빗썸 FAQ 크롤링 시작 (Playwright 사용)")
    logger.info("=" * 60)
    
    # MongoDB 연결
    logger.info("MongoDB Atlas 연결 중...")
    vector_store = AirflowVectorStore()
    connected = await vector_store.connect()
    if not connected:
        raise ConnectionError("MongoDB 연결 실패")
    
    logger.info("✅ MongoDB 연결 성공!")
    
    # Playwright 브라우저 시작
    logger.info("브라우저 시작 중...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ko-KR',
                timezone_id='Asia/Seoul',
            )
            
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {}
                };
            """)
            
            page = await context.new_page()
            logger.info("✅ 브라우저 시작 완료!")
            
            try:
                # 아티클 URL 발견
                logger.info("아티클 URL 발견 중...")
                article_urls = await discover_all_articles(page, limit=limit)
                
                if not article_urls:
                    logger.warning("아티클을 찾을 수 없습니다.")
                    return
                
                if limit:
                    article_urls = article_urls[:limit]
                
                logger.info(f"총 {len(article_urls)}개 아티클 발견")
                logger.info("크롤링 및 벡터 DB 저장 시작...")
                
                success_count = 0
                updated_count = 0
                skipped_count = 0
                fail_count = 0
                
                # 각 아티클 처리 및 저장
                for i, article_url in enumerate(article_urls, 1):
                    try:
                        logger.info(f"[{i}/{len(article_urls)}] 크롤링 중: {article_url}")
                        
                        # 아티클 내용 추출
                        article_data = await extract_article_content(page, article_url)
                        
                        if not article_data or not article_data.get("body"):
                            fail_count += 1
                            logger.warning(f"내용 추출 실패: {article_url}")
                            continue
                        
                        # 벡터 DB에 저장 (변경 감지 포함)
                        result = await vector_store.store_article(article_data)
                        
                        if result["status"] == "created":
                            success_count += 1
                            logger.info(f"✅ 신규 저장 완료: {article_data['title'][:40]}...")
                        elif result["status"] == "updated":
                            updated_count += 1
                            logger.info(f"🔄 업데이트 완료: {article_data['title'][:40]}...")
                        elif result["status"] == "migrated":
                            updated_count += 1  # 마이그레이션도 업데이트로 카운트
                            logger.info(f"🔄 마이그레이션 완료: {article_data['title'][:40]}... (content_hash 추가)")
                        elif result["status"] == "skipped":
                            skipped_count += 1
                            logger.info(f"⏭️  변경사항 없음 (스킵): {article_data['title'][:40]}...")
                        else:
                            fail_count += 1
                            logger.warning(f"저장 실패: {article_url}")
                        
                        await asyncio.sleep(1)  # Rate limit 방지
                        
                    except Exception as e:
                        fail_count += 1
                        logger.error(f"실패: {article_url} - {e}")
                        continue
                
                logger.info("=" * 60)
                logger.info(f"✅ 크롤링 완료!")
                logger.info(f"   신규 저장: {success_count}개")
                logger.info(f"   업데이트: {updated_count}개")
                logger.info(f"   변경 없음 (스킵): {skipped_count}개")
                logger.info(f"   실패: {fail_count}개")
                logger.info(f"   총 처리: {success_count + updated_count + skipped_count}개")
                logger.info("=" * 60)
                
            finally:
                await page.close()
                await context.close()
                await browser.close()
                logger.info("브라우저 종료 완료")
        
        except Exception as e:
            logger.error(f"브라우저 실행 오류: {e}")
            raise
    
    # MongoDB 연결 해제
    await vector_store.disconnect()
