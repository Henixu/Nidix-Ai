# RAG Studio 🔮
> Retrieval-Augmented Generation with Python + FastAPI + Groq

## Project Structure

```
rag_studio/
├── main.py              ← FastAPI server (RAG pipeline)
├── requirements.txt     ← Python dependencies
├── templates/
│   └── index.html       ← Frontend UI (served by FastAPI)
├── static/              ← Static assets (CSS/JS if needed)
└── README.md
```

## Setup

### 1. Set your Groq API key
```bash
# Linux/macOS
export GROQ_API_KEY="gsk_..."

# Windows PowerShell
$env:GROQ_API_KEY="gsk_..."
```

### 2. Create virtual environment & install dependencies
```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
# OR
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

If you are on Windows and already have Python 3.13 installed, prefer:
```bash
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The app now uses `sentence-transformers` to create embeddings and stores vectors in MongoDB for search.

### 3. Run the server
```bash
python main.py
# OR with auto-reload for development
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open the app
Go to → http://localhost:8000

---

## How it works

```
URL / Text
    ↓
[ Fetch & Clean ]  ← BeautifulSoup extracts text
    ↓
[ Split Chunks ]   ← Configurable size + overlap
    ↓
[ Embed + Store ]  ← Sentence-transformers embeddings stored in MongoDB
    ↓
User Question
    ↓
[ Embed Query ]    ← Same embedding model
    ↓
[ Retrieve Top-K ] ← Cosine similarity search
    ↓
[ Build Prompt ]   ← Context + question
    ↓
[ Groq Stream ]    ← SSE streaming to the browser
    ↓
Answer ✓
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web UI |
| POST | `/api/index` | Index a document |
| POST | `/api/query` | Query (non-streaming) |
| POST | `/api/query/stream` | Query with SSE streaming |
| GET | `/api/status` | Check Groq connection |
| GET | `/api/chunks` | List indexed chunks |

## Configuration (in UI)

| Parameter | Default | Description |
|-----------|---------|-------------|
| Chunk size | 500 | Characters per chunk |
| Overlap | 50 | Overlap between chunks |
| Top-K | 3 | Chunks retrieved per query |
| Temperature | 0.3 | LLM creativity (0=focused) |

## Vector storage

Vectors are stored in the MongoDB collection `car_vectors` by default. You can change the
collection name from the UI (hidden field) or in the API request payload.
