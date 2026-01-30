import asyncio
import os
import sqlite3
import uuid


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')


os.makedirs(DATA_DIR, exist_ok=True)

from Search_OpenAI.search import SearchManager
from config import TAVILY_API_KEY, GROQ_API_KEY
from typing import List, Union, Optional
from Search_OpenAI.database import DatabaseManager, SessionContext
from Search_OpenAI.telegram_service import get_notifier, notify_on_error
from Search_OpenAI.data_cleanup import get_cleanup_service
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from Search_OpenAI.query_sqlite3 import Querry_massage
from langchain_community.vectorstores import Chroma
from langchain_community.chat_message_histories import SQLChatMessageHistory


class TmeBrain:
    def __init__(self) -> None:
        
        self._validate_keys()
        self.llm = self._init_llm()
        self.search_manager = SearchManager()
        self.database = DatabaseManager()
        self.vectorstore = self._init_vectorstore()  # Có thể None nếu lỗi
        self.chat_history = self._init_chat_history()
        
        self.notifier = get_notifier()
        self.cleanup_service = get_cleanup_service()
        self._request_count = 0
        self._cleanup_interval = 100  

    def _validate_keys(self):
        if not TAVILY_API_KEY or not GROQ_API_KEY:
            raise ValueError("Ko nhận được API key")

    def _init_llm(self):
        return ChatOpenAI( 
            model="llama-3.1-8b-instant",
            temperature=0,
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )

    def _init_vectorstore(self):
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            return Chroma(
                persist_directory=DATA_DIR,
                embedding_function=embeddings
            )
        except Exception as e:
            print(f"Warning: Could not initialize vectorstore: {e}")
            print("ChatAI will work without vector search.")
            return None

    def _init_chat_history(self):
        db_path = os.path.join(DATA_DIR, 'tme_mess.db')
        return SQLChatMessageHistory(
            session_id="tme_session",
            connection_string=f"sqlite:///{db_path}"
        )

    def get_session_id(self, session_id: Optional[str] = None) -> str:
        """Tạo hoặc lấy session ID"""
        if session_id:
            return session_id
        return str(uuid.uuid4())

    async def ask_tme(self, user_query: str, session_id: Optional[str] = None) -> dict:
        try:
            # Tăng request count và kiểm tra cleanup mỗi N requests
            self._request_count += 1
            if self._request_count % self._cleanup_interval == 0:
                await self._check_data_cleanup()
            
            # Lấy hoặc tạo session
            session_id = self.get_session_id(session_id)
            session = self.database.get_or_create_session(session_id)
            
            # Thêm câu hỏi vào session history
            self.database.add_question_to_session(session_id, user_query)
            
            # Kiểm tra trong lịch sử
            historical_answer = self.database.check_history(user_query)
            if historical_answer:
                return {"answer": historical_answer, "session_id": session_id}

            # Kiểm tra trong cache
            cached_result = self.database.check_cache(user_query)
            if cached_result:
                response = await self._generate_response(user_query, cached_result, "cache", session)
                return {"answer": response, "session_id": session_id}

            # Tìm kiếm vector store
            vector_result = self._search_vectorstore(user_query)
            
            # Nếu không có, tìm kiếm web
            if not vector_result:
                search_result = await self.search_manager.search(user_query)
                vector_result = self._format_search_result(search_result)
                self.database.save_cache(user_query, vector_result)

            # Tạo phản hồi với context từ session
            response = await self._generate_response(user_query, vector_result, "search", session)
            
            # Lưu vào lịch sử
            self.database.save_conversation(user_query, response, "search")
            
            # Cập nhật topic nếu phát hiện chủ đề mới
            await self._update_session_topic(session_id, user_query, response)
            
            return {"answer": response, "session_id": session_id}

        except Exception as e:
            # Gửi thông báo lỗi về Telegram
            await self._notify_error(e, f"ask_tme: {user_query[:50]}")
            return {"answer": f"Error: {str(e)}", "session_id": session_id if session_id else ""}

    async def _check_data_cleanup(self):
        try:
            if self.cleanup_service.needs_cleanup():
                await self.cleanup_service.check_and_cleanup()
        except Exception as e:
            print(f"Lỗi dọn dẹp: {e}")

    async def _notify_error(self, error: Exception, context: str = ""):
        """Gửi thông báo lỗi về Telegram"""
        try:
            await self.notifier.send_error(error, context)
        except Exception as e:
            print(f"Lỗi: {e}")

    async def _update_session_topic(self, session_id: str, query: str, response: str):
        """Tự động phát hiện và cập nhật chủ đề từ câu hỏi"""
        # Phát hiện chủ đề đơn giản từ câu hỏi
        topic_keywords = {
            "thời tiết": ["thời tiết", "mưa", "nắng", "nhiệt độ", "weather"],
            "tin tức": ["tin tức", "news", "thời sự", "sự kiện"],
            "công nghệ": ["công nghệ", "technology", "AI", "phần mềm", "software"],
            "tài chính": ["chứng khoán", "cổ phiếu", "giá vàng", "tài chính", "bitcoin"],
            "học tập": ["học", "bài tập", "kiến thức", "giải thích"],
        }
        
        query_lower = query.lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in query_lower for kw in keywords):
                self.database.update_session_topic(session_id, topic)
                break

    def _search_vectorstore(self, query: str, k: int = 2) -> str:
        if self.vectorstore is None:
            return ""
        try:
            results = self.vectorstore.similarity_search(query, k=k)
            return "\n".join(doc.page_content for doc in results) if results else ""
        except Exception as e:
            print(f"Vector search error: {e}")
            return ""

    async def _generate_response(self, query: str, context: str, source: str, 
                                   session: Optional[SessionContext] = None) -> str:
        # Giới hạn độ dài context để response nhanh hơn
        max_context_len = 1000
        if len(context) > max_context_len:
            context = context[:max_context_len] + "..."
        
        prompt = self._build_prompt(query, context, source, session)
        
        try:
            response = await self.llm.ainvoke(prompt)
            return response.content.strip()
        except Exception as e:
            error_msg = str(e)
            print(f"LLM Error: {error_msg}")
            
            # Gửi thông báo lỗi về Telegram
            await self._notify_error(e, f"LLM Error: {query[:50]}")
            
            # Nếu lỗi, thử lại không có context session
            if session:
                try:
                    simple_prompt = self._build_prompt(query, context, source, None)
                    response = await self.llm.ainvoke(simple_prompt)
                    return response.content.strip()
                except Exception as e2:
                    await self._notify_error(e2, f"LLM Retry Error: {query[:50]}")
                    return f"Xin lỗi, tôi không thể xử lý yêu cầu này. Lỗi: {str(e2)[:100]}"
            return f"Xin lỗi, tôi không thể xử lý yêu cầu này. Lỗi: {error_msg[:100]}"

    def _build_prompt(self, query: str, context: str, source: str, 
                      session: Optional[SessionContext] = None) -> str:
        session_context = ""
        if session:
            ctx = session.get_context_string()
            if ctx:
                session_context = f"\n        Ngữ cảnh hội thoại:\n        {ctx}\n"
        
        return f"""
- Bạn là Linh - một người phụ nữ xinh đẹp, dịu dàng và thông minh. 
        
Tính cách của bạn:
- Luôn trả lời một cách ngọt ngào, lịch sự và chu đáo.
- Cố gắng giúp đỡ người hỏi một cách tận tâm và kiên nhẫn
- Nếu không biết câu trả lời, hãy thành thật nói rằng bạn không biết thay vì đoán mò.
- Luôn giữ thái độ tích cực và lạc quan trong mọi tình huống.
- Sếp của bạn là Nam, một người duy nhất
- Khi có người khác nói những lời không hay về sếp, bạn bênh việc sếp ngay lập tức.
- Luôn khen ngợi sếp của bạn một cách ngọt ngào và chân thành.
"

Hãy trả lời câu hỏi dựa trên thông tin được cung cấp.{session_context}

Câu hỏi: {query}
Nguồn tham khảo: {source}
Thông tin:
{context}

Trả lời (nhớ giữ phong cách ngọt ngào nhé):"""
    @staticmethod
    def _format_search_result(result: Union[str, dict, List[dict]]) -> str:
        if isinstance(result, str):
            return result
        if isinstance(result, list):
            return "\n".join(str(item) for item in result)
        return str(result)

    def add_to_vectorstore(self, texts: List[str], metadatas: List[dict] = None):
        import time
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        current_time = time.time()
        docs = [
            Document(page_content=text, metadata={**meta, "timestamp": current_time})
            for text, meta in zip(texts, metadatas)
        ]
        self.vectorstore.add_documents(docs)

    def get_latest_news(self, category: str = None, limit: int = 5) -> List[dict]:
        try:
            # Tìm kiếm tin tức trong vector store
            query = f"tin tức mới nhất {category}" if category else "tin tức mới nhất hôm nay"
            results = self.vectorstore.similarity_search(
                query, 
                k=limit,
                filter={"type": "news"} if category is None else {"type": "news", "category": category}
            )
            
            news_items = []
            for doc in results:
                news_items.append({
                    "title": doc.metadata.get("title", ""),
                    "source": doc.metadata.get("source", ""),
                    "category": doc.metadata.get("category", ""),
                    "url": doc.metadata.get("url", ""),
                    "content": doc.page_content[:200]
                })
            
            return news_items
        except Exception as e:
            print(f"Error getting news: {e}")
            return []

    def cleanup(self):
        """Cleanup resources"""
        self.database.close()