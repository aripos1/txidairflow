"""
Airflow 전용 MongoDB 벡터 저장소 모듈
app과 완전히 분리된 독립적인 모듈
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from openai import AsyncOpenAI
import hashlib
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AirflowVectorStore:
    """Airflow 전용 MongoDB Atlas 벡터 저장소"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        # OpenAI 클라이언트는 API 키가 있을 때만 초기화
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = AsyncOpenAI(api_key=api_key)
        else:
            self.openai_client = None
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        
    async def connect(self):
        """MongoDB 연결"""
        try:
            connection_string = os.getenv("MONGODB_URI")
            database_name = os.getenv("MONGODB_DATABASE", "chatbot_db")
            
            if not connection_string:
                logger.error("MONGODB_URI 환경변수가 설정되지 않았습니다.")
                return False
            
            self.client = AsyncIOMotorClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=1
            )
            
            # 연결 테스트
            await asyncio.wait_for(
                self.client.admin.command('ping'),
                timeout=5.0
            )
            
            self.db = self.client[database_name]
            self.collection = self.db["knowledge_base"]
            
            logger.info("MongoDB Atlas 벡터 DB 연결 성공")
            return True
            
        except asyncio.TimeoutError:
            logger.warning("MongoDB 벡터 DB 연결 타임아웃 (5초)")
            return False
        except ConnectionFailure as e:
            logger.error(f"MongoDB 벡터 DB 연결 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"MongoDB 벡터 DB 연결 오류: {e}")
            return False
    
    async def disconnect(self):
        """MongoDB 연결 해제"""
        if self.client:
            self.client.close()
    
    def split_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """텍스트를 청크로 분할"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # 문장 경계 찾기
            if '\n\n' in text[start:end]:
                last_break = text.rfind('\n\n', start, end)
                if last_break != -1:
                    end = last_break + 2
            elif '\n' in text[start:end]:
                last_break = text.rfind('\n', start, end)
                if last_break != -1:
                    end = last_break + 1
            elif '.' in text[start:end]:
                last_dot = text.rfind('.', start, end)
                if last_dot != -1:
                    end = last_dot + 1
            
            chunks.append(text[start:end].strip())
            start = end - overlap
        
        return chunks
    
    async def create_embedding(self, text: str) -> Optional[List[float]]:
        """텍스트 임베딩 생성"""
        if not self.openai_client:
            logger.error("OpenAI API 키가 설정되지 않았습니다. OPENAI_API_KEY 환경 변수를 설정하세요.")
            return None
        
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            return None
    
    async def check_article_exists(self, article_id: str) -> Optional[Dict]:
        """아티클이 이미 저장되어 있는지 확인"""
        if self.collection is None:
            return None
        
        try:
            # 해당 아티클의 첫 번째 청크를 찾음 (article_id로 검색)
            existing_doc = await self.collection.find_one({
                "metadata.article_id": article_id,
                "metadata.chunk_index": 0
            })
            return existing_doc
        except Exception as e:
            logger.error(f"아티클 존재 확인 실패 ({article_id}): {e}")
            return None
    
    def calculate_content_hash(self, text: str) -> str:
        """텍스트 내용의 해시 계산 (변경 감지용)"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    async def store_article(self, article_data: Dict) -> Dict:
        """
        아티클을 벡터 DB에 저장
        반환값: {"status": "created|updated|skipped", "chunks": 저장된 청크 수}
        """
        if self.collection is None:
            logger.error("MongoDB가 연결되지 않았습니다.")
            return {"status": "error", "chunks": 0}
        
        article_id = article_data.get("article_id")
        if not article_id:
            logger.error("article_id가 없습니다.")
            return {"status": "error", "chunks": 0}
        
        try:
            # 텍스트를 청크로 분할
            text = article_data["full_text"]
            chunks = self.split_text(text, chunk_size=1000, overlap=200)
            
            # 전체 텍스트 해시 계산 (변경 감지용)
            content_hash = self.calculate_content_hash(text)
            
            # 기존 문서 확인
            existing_doc = await self.check_article_exists(article_id)
            
            status = "created"  # 기본값: 신규 생성
            if existing_doc:
                # 기존 문서의 해시 비교 (메타데이터에 저장된 해시 사용)
                existing_hash = existing_doc.get("metadata", {}).get("content_hash")
                
                if existing_hash is None:
                    # 기존 데이터에 content_hash가 없는 경우 (구버전 데이터)
                    # 기존 텍스트 내용과 비교하여 변경 여부 확인
                    existing_text = existing_doc.get("text", "")
                    existing_title = existing_doc.get("metadata", {}).get("title", "")
                    
                    # 첫 번째 청크의 텍스트만으로 빠른 비교
                    # full_text가 아닌 body만 비교 (제목 포함 여부 차이 무시)
                    body_text = article_data.get("body", "")
                    
                    # 간단한 비교: 첫 500자 비교
                    existing_preview = existing_text[:500] if existing_text else ""
                    new_preview = body_text[:500] if body_text else ""
                    
                    if existing_title == article_data.get("title", "") and existing_preview == new_preview:
                        # 제목과 첫 부분이 같으면 변경 없음으로 간주
                        # 하지만 content_hash가 없으므로 마이그레이션 겸 업데이트
                        logger.info(f"아티클 {article_id} 기존 데이터 감지 (content_hash 없음) - 마이그레이션 업데이트")
                        # 해당 아티클의 모든 청크 삭제 후 재저장 (content_hash 추가)
                        delete_result = await self.collection.delete_many({
                            "metadata.article_id": article_id
                        })
                        logger.info(f"기존 청크 {delete_result.deleted_count}개 삭제됨 (마이그레이션)")
                        status = "migrated"  # 마이그레이션 상태
                    else:
                        # 내용이 다르면 업데이트
                        logger.info(f"아티클 {article_id} 내용 변경 감지 - 업데이트 시작")
                        delete_result = await self.collection.delete_many({
                            "metadata.article_id": article_id
                        })
                        logger.info(f"기존 청크 {delete_result.deleted_count}개 삭제됨")
                        status = "updated"
                        
                elif existing_hash == content_hash:
                    # 내용이 변경되지 않음 (해시 일치)
                    logger.info(f"아티클 {article_id} 변경사항 없음 (스킵)")
                    return {"status": "skipped", "chunks": 0}
                else:
                    # 내용이 변경됨 - 기존 청크 삭제 후 재저장
                    logger.info(f"아티클 {article_id} 내용 변경 감지 - 업데이트 시작")
                    # 해당 아티클의 모든 청크 삭제
                    delete_result = await self.collection.delete_many({
                        "metadata.article_id": article_id
                    })
                    logger.info(f"기존 청크 {delete_result.deleted_count}개 삭제됨")
                    status = "updated"
            
            # 신규 저장 또는 업데이트
            stored_count = 0
            for i, chunk in enumerate(chunks):
                try:
                    # 임베딩 생성
                    embedding = await self.create_embedding(chunk)
                    if not embedding:
                        continue
                    
                    # 문서 ID 생성
                    doc_id = hashlib.md5(
                        f"zendesk_{article_id}_{i}".encode()
                    ).hexdigest()
                    
                    # 메타데이터 생성
                    metadata = {
                        "article_id": article_id,
                        "title": article_data["title"],
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "type": "zendesk_article",
                        "content_hash": content_hash,  # 변경 감지를 위한 해시 저장
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    # URL 정보 추가
                    if article_data.get("url"):
                        metadata["url"] = article_data["url"]
                    
                    # 섹션/카테고리 정보 추가
                    if article_data.get("section_name"):
                        metadata["section_name"] = article_data["section_name"]
                    if article_data.get("category_name"):
                        metadata["category_name"] = article_data["category_name"]
                    
                    # 이미지 정보 추가 (모든 청크에 포함 - 검색 시 이미지 정보 접근 가능)
                    if article_data.get("images"):
                        metadata["images"] = article_data["images"]
                    
                    # MongoDB에 저장
                    document = {
                        "_id": doc_id,
                        "text": chunk,
                        "source": article_data.get("url", ""),
                        "metadata": metadata,
                        "embedding": embedding,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    
                    await self.collection.update_one(
                        {"_id": doc_id},
                        {"$set": document},
                        upsert=True
                    )
                    
                    stored_count += 1
                    
                except Exception as e:
                    logger.error(f"청크 저장 실패 (아티클 {article_id}, 청크 {i}): {e}")
                    continue
            
            status_msg = {
                "created": "신규 저장",
                "updated": "업데이트",
                "skipped": "스킵"
            }.get(status, status)
            
            logger.info(f"아티클 {article_id} {status_msg} 완료: {stored_count}/{len(chunks)} 청크")
            return {"status": status, "chunks": stored_count}
            
        except Exception as e:
            logger.error(f"아티클 저장 실패 ({article_id}): {e}")
            return {"status": "error", "chunks": 0}
