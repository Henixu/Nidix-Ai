"""
RAG Studio — FastAPI Backend
Retrieval-Augmented Generation with Groq
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import os
import httpx
import json
import re
import asyncio
import logging
import unicodedata
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Studio", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Prompt size tuning (helps response time for large models).
MAX_CHUNK_CHARS = 1200
MAX_CONTEXT_CHARS = 6000
DEFAULT_NUM_PREDICT = 256
# Groq API config
DEFAULT_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_VECTOR_COLLECTION = "car_vectors"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

# ─── Mongo-backed vector store (embeddings) ───────────────────────────────────
_embedding_model = None


def _get_embedding_model():
    if SentenceTransformer is None:
        raise HTTPException(
            500,
            "sentence-transformers is not installed. Run: pip install sentence-transformers"
        )
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(DEFAULT_EMBEDDING_MODEL)
    return _embedding_model


def _embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_embedding_model()
    return model.encode(texts, normalize_embeddings=True).tolist()


class VectorStore:
    def __init__(self):
        self.chunks: list[str] = []
        self.embeddings: list[list[float]] = []
        self.source: str = ""
        self.car_records: list[dict] = []
        self.mongo_uri: str = ""
        self.mongo_db: str = ""
        self.vector_collection: str = DEFAULT_VECTOR_COLLECTION

    def clear(self):
        self.chunks = []
        self.embeddings = []
        self.source = ""
        self.car_records = []
        self.mongo_uri = ""
        self.mongo_db = ""
        self.vector_collection = DEFAULT_VECTOR_COLLECTION

    def build(
        self,
        chunks: list[str],
        source: str = "",
        mongo_uri: str = "",
        mongo_db: str = "",
        vector_collection: str = DEFAULT_VECTOR_COLLECTION
    ):
        self.chunks = chunks
        self.source = source
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.vector_collection = vector_collection or DEFAULT_VECTOR_COLLECTION

        self.embeddings = _embed_texts(chunks)
        if self.mongo_uri and self.mongo_db:
            self._persist_vectors()

    def _persist_vectors(self):
        if MongoClient is None:
            raise HTTPException(
                500,
                "pymongo is not installed. Run: pip install pymongo"
            )

        client = None
        try:
            client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            collection = client[self.mongo_db][self.vector_collection]

            collection.delete_many({})
            docs = []
            for i, (chunk, embedding) in enumerate(zip(self.chunks, self.embeddings)):
                docs.append({
                    "index": i,
                    "chunk": chunk,
                    "embedding": embedding,
                    "source": self.source
                })
            if docs:
                collection.insert_many(docs)
        except Exception as exc:
            raise HTTPException(400, f"MongoDB error: {str(exc)}")
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    def load_from_mongo(
        self,
        mongo_uri: str,
        mongo_db: str,
        vector_collection: str
    ):
        if MongoClient is None:
            raise HTTPException(
                500,
                "pymongo is not installed. Run: pip install pymongo"
            )

        client = None
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            collection = client[mongo_db][vector_collection]
            docs = list(collection.find({}, {
                "_id": 0,
                "index": 1,
                "chunk": 1,
                "embedding": 1,
                "source": 1
            }))
            if not docs:
                raise HTTPException(
                    400,
                    f"No vectors found in {mongo_db}.{vector_collection}."
                )

            docs.sort(key=lambda d: d.get("index", 0))
            self.chunks = [d.get("chunk", "") for d in docs]
            self.embeddings = [d.get("embedding", []) for d in docs]
            self.source = docs[0].get("source", "")
            self.mongo_uri = mongo_uri
            self.mongo_db = mongo_db
            self.vector_collection = vector_collection
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(400, f"MongoDB error: {str(exc)}")
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    def _dot(self, a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        mongo_uri: str = "",
        mongo_db: str = "",
        vector_collection: str = ""
    ) -> list[dict]:
        if not self.embeddings:
            if mongo_uri and mongo_db:
                self.load_from_mongo(
                    mongo_uri=mongo_uri,
                    mongo_db=mongo_db,
                    vector_collection=vector_collection or DEFAULT_VECTOR_COLLECTION
                )
            else:
                return []

        q_vec = _embed_texts([query])[0]
        scored = []
        for i, embedding in enumerate(self.embeddings):
            if not embedding:
                continue
            score = self._dot(q_vec, embedding)
            scored.append({
                "index": i,
                "chunk": self.chunks[i],
                "score": float(score)
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


vector_store = VectorStore()


# ─── Text processing ──────────────────────────────────────────────────────────
def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = re.sub(r'\s+', ' ', text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            last_period = text.rfind('.', start + chunk_size // 2, end)
            if last_period != -1:
                end = last_period + 1
        chunk = text[start:min(end, len(text))].strip()
        if len(chunk) > 20:
            chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks


async def fetch_url_text(url: str) -> str:
    from bs4 import BeautifulSoup
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        try:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            page_text = r.text
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (403, 429):
                raise
            proxy_url = f"https://r.jina.ai/http://{url}"
            proxy_response = await client.get(proxy_url, headers=headers)
            proxy_response.raise_for_status()
            page_text = proxy_response.text

    soup = BeautifulSoup(page_text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return re.sub(r'\s+', ' ', soup.get_text(separator=' ')).strip()


# ─── Pydantic Models ──────────────────────────────────────────────────────────
class IndexRequest(BaseModel):
    source_type: str          # "url", "text", or "mongodb"
    content: str = ""         # URL or raw text
    chunk_size: int = 500
    chunk_overlap: int = 50
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "Nidix"
    mongo_collection: str = "cars2"
    vector_collection: str = DEFAULT_VECTOR_COLLECTION
    mongo_limit: Optional[int] = None


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    model: str = DEFAULT_GROQ_MODEL
    temperature: float = 0.5
    max_tokens: int = DEFAULT_NUM_PREDICT
    groq_api_key: Optional[str] = None
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "Nidix"
    vector_collection: str = DEFAULT_VECTOR_COLLECTION


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def _serialize_car_document(doc: dict) -> str:
    """Convert one MongoDB car document to rich text for chunking/retrieval."""
    clean_doc = {k: v for k, v in doc.items() if k != "_id"}
    return json.dumps(clean_doc, ensure_ascii=False, indent=2)


def _safe_get(d: Optional[dict], key: str, default=None):
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value).lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[_\-/:]", " ", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _trim_chunk_for_prompt(chunk: str, max_chars: int = MAX_CHUNK_CHARS) -> str:
    # Drop raw JSON payloads and clamp size to reduce prompt latency.
    if "raw_json:" in chunk:
        chunk = chunk.split("raw_json:", 1)[0].rstrip()
    if len(chunk) <= max_chars:
        return chunk
    trimmed = chunk[:max_chars]
    last_space = trimmed.rfind(" ")
    if last_space > 200:
        trimmed = trimmed[:last_space]
    return trimmed.rstrip() + "..."


def _build_context(results: list[dict], max_context_chars: int = MAX_CONTEXT_CHARS) -> str:
    parts = []
    total = 0
    for i, r in enumerate(results):
        chunk_text = _trim_chunk_for_prompt(r["chunk"])
        entry = f"[{i+1}] {chunk_text}"
        entry_len = len(entry) + 2
        if parts and total + entry_len > max_context_chars:
            break
        parts.append(entry)
        total += entry_len
    return "\n\n".join(parts)


def _car_doc_to_chunk(doc: dict, index: int) -> str:
    marque = str(doc.get("marque", "Unknown"))
    modele = str(doc.get("modele", "Unknown"))
    annee = doc.get("annee", "N/A")
    vehicle_type = doc.get("type_vehicule", "N/A")
    body = doc.get("carrosserie", "N/A")
    segment = doc.get("segment", "N/A")

    motor = doc.get("motorisation", {}) or {}
    price = doc.get("prix", {}) or {}
    dims = doc.get("dimensions", {}) or {}
    warranty = doc.get("garantie", {}) or {}

    record_id = doc.get("_id", f"car_{index+1}")
    colors = doc.get("couleurs_disponibles", []) or []
    colors_text = ", ".join(colors[:6]) if colors else "N/A"
    equipment = doc.get("equipements", []) or []
    equipment_text = ", ".join(equipment[:10]) if equipment else "N/A"

    reviews = doc.get("avis", []) or []
    review_count = len(reviews)
    avg_rating = round(
        sum(float(r.get("note", 0)) for r in reviews) / review_count, 2
    ) if review_count else "N/A"

    raw_json = _serialize_car_document(doc)

    return (
        f"CAR_PROFILE {index+1}\n"
        f"id: {record_id}\n"
        f"marque: {marque}\n"
        f"modele: {modele}\n"
        f"annee: {annee}\n"
        f"type_vehicule: {vehicle_type}\n"
        f"carrosserie: {body}\n"
        f"segment: {segment}\n"
        f"constructeur_pays: {_safe_get(doc.get('constructeur'), 'pays', 'N/A')}\n"
        f"type_carburant: {_safe_get(motor, 'type_carburant', 'N/A')}\n"
        f"transmission: {_safe_get(motor, 'transmission', 'N/A')}\n"
        f"puissance_ch: {_safe_get(motor, 'puissance_ch', 'N/A')}\n"
        f"couple_nm: {_safe_get(motor, 'couple_nm', 'N/A')}\n"
        f"consommation_l100km: {_safe_get(motor, 'consommation_l100km', 'N/A')}\n"
        f"consommation_kwh100km: {_safe_get(motor, 'consommation_kwh100km', 'N/A')}\n"
        f"emissions_co2_gkm: {_safe_get(motor, 'emissions_co2_gkm', 'N/A')}\n"
        f"autonomie_km: {_safe_get(motor, 'autonomie_km', 'N/A')}\n"
        f"batterie_kwh: {_safe_get(motor, 'batterie_kwh', 'N/A')}\n"
        f"prix_total_ttc_eur: {_safe_get(price, 'prix_total_ttc_eur', 'N/A')}\n"
        f"prix_base_eur: {_safe_get(price, 'prix_base_eur', 'N/A')}\n"
        f"loyer_mensuel_eur: {_safe_get(price, 'loyer_mensuel_eur', 'N/A')}\n"
        f"coffre_litres: {_safe_get(dims, 'coffre_litres', 'N/A')}\n"
        f"nombre_places: {_safe_get(dims, 'nombre_places', 'N/A')}\n"
        f"nombre_portes: {_safe_get(dims, 'nombre_portes', 'N/A')}\n"
        f"garantie_duree_ans: {_safe_get(warranty, 'duree_ans', 'N/A')}\n"
        f"avis_count: {review_count}\n"
        f"avis_note_moyenne: {avg_rating}\n"
        f"couleurs: {colors_text}\n"
        f"equipements_cles: {equipment_text}\n"
        f"raw_json:\n{raw_json}"
    )


def load_cars_chunks_from_mongodb(
    mongo_uri: str,
    db_name: str,
    collection_name: str,
    limit: Optional[int] = None
) -> tuple[list[str], list[dict], int]:
    if MongoClient is None:
        raise HTTPException(
            500,
            "pymongo is not installed. Run: pip install pymongo"
        )

    client = None
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        collection = client[db_name][collection_name]

        cursor = collection.find({})
        if limit and limit > 0:
            cursor = cursor.limit(limit)

        docs = list(cursor)
        if not docs:
            raise HTTPException(
                400,
                f"No documents found in {db_name}.{collection_name}."
            )

        chunks = [_car_doc_to_chunk(doc, i) for i, doc in enumerate(docs)]
        return chunks, docs, len(docs)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"MongoDB error: {str(exc)}")
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


@app.post("/api/index")
async def index_document(req: IndexRequest):
    try:
        chunks: list[str] = []
        if req.source_type == "url":
            text = await fetch_url_text(req.content)
            chunks = split_text(text, req.chunk_size, req.chunk_overlap)
            vector_store.car_records = []
        elif req.source_type == "mongodb":
            chunks, docs, doc_count = load_cars_chunks_from_mongodb(
                mongo_uri=req.mongo_uri,
                db_name=req.mongo_db,
                collection_name=req.mongo_collection,
                limit=req.mongo_limit
            )
            vector_store.car_records = docs
            logger.info(
                f"Loaded {doc_count} docs from MongoDB {req.mongo_db}.{req.mongo_collection}"
            )
        else:
            text = req.content.strip()
            chunks = split_text(text, req.chunk_size, req.chunk_overlap)
            vector_store.car_records = []

        if not chunks:
            raise HTTPException(400, "No chunks were created from the selected source.")

        source_value = req.content
        mongo_uri = ""
        mongo_db = ""
        if req.source_type == "mongodb":
            source_value = f"mongodb://{req.mongo_db}/{req.mongo_collection}"
            mongo_uri = req.mongo_uri
            mongo_db = req.mongo_db

        vector_store.build(
            chunks,
            source=source_value,
            mongo_uri=mongo_uri,
            mongo_db=mongo_db,
            vector_collection=req.vector_collection
        )
        logger.info(f"Indexed {len(chunks)} chunks from: {source_value[:60]}")

        return {
            "success": True,
            "chunk_count": len(chunks),
            "chunks": [
                {"index": i, "text": c, "length": len(c)}
                for i, c in enumerate(chunks)
            ]
        }
    except httpx.HTTPError as e:
        raise HTTPException(400, f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        raise HTTPException(500, str(e))


def build_car_rag_prompt(question: str, context: str) -> str:
    return f"""You are CarRAG, a creative automotive advisor for vehicle comparison and analysis.
You must answer using ONLY the CONTEXT below.

Rules:
- If the answer is not in context, say: "I don't have enough data in the indexed cars collection."
- Prefer exact values (price, power, consommation, emissions, autonomie) from context.
- For comparisons, present both cars clearly and mention key differences.
- Do not invent missing specs.
- Avoid dumping raw fields; synthesize into an engaging, helpful response.

Answer style:
- Start with a short, engaging summary (2-4 sentences) with the key tradeoffs.
- Then add a compact "Key evidence" list with exact specs from the context.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""


def _resolve_groq_key(req_key: Optional[str]) -> str:
    key = (req_key or "").strip() or DEFAULT_GROQ_API_KEY
    if not key:
        raise HTTPException(
            500,
            "Groq API key is missing. Set GROQ_API_KEY or pass groq_api_key."
        )
    return key


async def _groq_chat_completion(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    api_key: str
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max(1, max_tokens)
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(GROQ_CHAT_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def try_answer_dealers_question(question: str) -> Optional[dict]:
    """Deterministic answer for dealer/concessionnaire requests from indexed car docs."""
    if not vector_store.car_records:
        return None

    q = _normalize_text(question)
    dealer_keywords = ["concessionnaire", "concessionnaires", "dealer", "dealers", "garage"]
    if not any(k in q for k in dealer_keywords):
        return None

    matches = []
    for i, doc in enumerate(vector_store.car_records):
        marque = _normalize_text(str(doc.get("marque", "")))
        modele = _normalize_text(str(doc.get("modele", "")))
        query_has_brand = bool(marque) and marque in q
        query_has_model = bool(modele) and modele in q
        if query_has_brand or query_has_model:
            matches.append((i, doc))

    if not matches:
        return None

    dealers = []
    dealer_seen = set()
    target_labels = []

    for i, doc in matches:
        marque = str(doc.get("marque", "Unknown"))
        modele = str(doc.get("modele", "Unknown"))
        target_labels.append(f"{marque} {modele}")

        for dealer in doc.get("concessionnaires", []) or []:
            name = str(dealer.get("name", "Unknown"))
            city = str(dealer.get("city", "Unknown city"))
            country = str(dealer.get("country", "Unknown country"))
            key = _normalize_text(f"{name}|{city}|{country}")
            if key in dealer_seen:
                continue
            dealer_seen.add(key)
            dealers.append(f"- {name} ({city}, {country})")

    if not dealers:
        answer = (
            f"Je n'ai trouve aucun concessionnaire renseigne pour: "
            f"{', '.join(sorted(set(target_labels)))}."
        )
    else:
        answer = (
            f"Concessionnaires trouves pour {', '.join(sorted(set(target_labels)))}:\n"
            + "\n".join(dealers)
        )

    sources = [
        {"index": i, "chunk": vector_store.chunks[i], "score": 1.0}
        for i, _doc in matches
        if i < len(vector_store.chunks)
    ][:8]

    return {"answer": answer, "sources": sources}


@app.post("/api/query")
async def query_document(req: QueryRequest):
    deterministic = try_answer_dealers_question(req.question)
    if deterministic is not None:
        return {
            "answer": deterministic["answer"],
            "sources": deterministic["sources"],
            "model": req.model,
            "pipeline": ["detect dealer query", "filter indexed cars", "return grounded answer"]
        }

    # Retrieve
    results = vector_store.retrieve(
        req.question,
        req.top_k,
        mongo_uri=req.mongo_uri,
        mongo_db=req.mongo_db,
        vector_collection=req.vector_collection
    )
    if not results:
        raise HTTPException(400, "No vectors indexed yet. Run indexing first.")
    context = _build_context(results)

    prompt = build_car_rag_prompt(req.question, context)
    messages = [{"role": "user", "content": prompt}]

    # Call Groq
    try:
        api_key = _resolve_groq_key(req.groq_api_key)
        answer = await _groq_chat_completion(
            messages=messages,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            api_key=api_key
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(500, f"Groq error: {exc.response.text}")
    except Exception as e:
        raise HTTPException(500, f"Groq error: {str(e)}")

    return {
        "answer": answer,
        "sources": results,
        "model": req.model,
        "pipeline": ["embed query", f"retrieve top-{req.top_k}", "build prompt", "generate"]
    }


@app.post("/api/query/stream")
async def query_stream(req: QueryRequest):
    """Streaming version using SSE"""
    deterministic = try_answer_dealers_question(req.question)
    if deterministic is not None:
        async def deterministic_stream():
            yield f"data: {json.dumps({'type': 'sources', 'sources': deterministic['sources']})}\n\n"
            for part in deterministic["answer"].split(" "):
                yield f"data: {json.dumps({'type': 'token', 'text': part + ' '})}\n\n"
                await asyncio.sleep(0.005)
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(deterministic_stream(), media_type="text/event-stream")

    results = vector_store.retrieve(
        req.question,
        req.top_k,
        mongo_uri=req.mongo_uri,
        mongo_db=req.mongo_db,
        vector_collection=req.vector_collection
    )
    if not results:
        raise HTTPException(400, "No vectors indexed yet. Run indexing first.")
    context = _build_context(results)
    prompt = build_car_rag_prompt(req.question, context)

    async def stream_generator():
        # First send sources
        yield f"data: {json.dumps({'type': 'sources', 'sources': results})}\n\n"

        try:
            api_key = _resolve_groq_key(req.groq_api_key)
            payload = {
                "model": req.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": req.temperature,
                "max_tokens": max(1, req.max_tokens),
                "stream": True
            }
            headers = {"Authorization": f"Bearer {api_key}"}

            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    GROQ_CHAT_URL,
                    headers=headers,
                    json=payload
                ) as r:
                    async for line in r.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            yield f"data: {json.dumps({'type': 'done'})}\n\n"
                            break
                        try:
                            evt = json.loads(data)
                            delta = evt.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@app.get("/api/status")
async def status(groq_api_key: Optional[str] = None):
    key = (groq_api_key or "").strip() or DEFAULT_GROQ_API_KEY
    if not key:
        return {"connected": False, "models": []}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {key}"}
            )
            r.raise_for_status()
            data = r.json()
            models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
            return {"connected": True, "models": models}
    except Exception:
        return {"connected": False, "models": []}


@app.get("/api/chunks")
async def get_chunks():
    return {
        "chunks": [{"index": i, "text": c, "length": len(c)}
                   for i, c in enumerate(vector_store.chunks)],
        "source": vector_store.source
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
