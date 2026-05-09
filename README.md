# RAG Studio 🔮
> Retrieval-Augmented Generation with Python + FastAPI + Ollama

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

### 1. Install Ollama
```bash
# Linux / WSL
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama
```

### 2. Pull a model
```bash
ollama pull llama3.2        # recommended (2GB)
# or
ollama pull mistral         # alternative (4GB)
ollama pull phi3            # lightweight (2GB)
```

### 3. Start Ollama with CORS enabled
```bash
OLLAMA_ORIGINS=* ollama serve
```

### 4. Create virtual environment & install dependencies
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

The app currently runs without `scikit-learn` or `chromadb`; those packages are only needed if you add the optional embedding upgrade.

### 5. Run the server
```bash
python main.py
# OR with auto-reload for development
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Open the app
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
[ TF-IDF Index ]   ← In-memory vector store (scikit-learn)
    ↓
User Question
    ↓
[ Embed Query ]    ← TF-IDF on the question
    ↓
[ Retrieve Top-K ] ← Cosine similarity search
    ↓
[ Build Prompt ]   ← Context + question
    ↓
[ Ollama Stream ]  ← SSE streaming to the browser
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
| GET | `/api/status` | Check Ollama connection |
| GET | `/api/chunks` | List indexed chunks |

## Configuration (in UI)

| Parameter | Default | Description |
|-----------|---------|-------------|
| Chunk size | 500 | Characters per chunk |
| Overlap | 50 | Overlap between chunks |
| Top-K | 3 | Chunks retrieved per query |
| Temperature | 0.3 | LLM creativity (0=focused) |

## Upgrade: Use real embeddings (optional)

To replace TF-IDF with real vector embeddings, install:
```bash
pip install sentence-transformers chromadb
```

Then in `main.py`, replace the `VectorStore` class with ChromaDB + 
`sentence-transformers` embeddings for production-grade semantic search.
