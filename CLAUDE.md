# QualysGPT — Project Context


## What This Is
- RAG-powered agentic chatbot over Qualys certification notes
- Stack: Python, Qdrant (Docker), OpenAI embeddings, LangGraph, Claude API, FastMCP, Chainlit
- Dev OS: Windows — use pathlib.Path for ALL file paths, never string concatenation
- All terminal commands written for PowerShell


## Project Structure
- data/urls.json — shared URL file, all certs (has cert_name field per entry)
- data/raw/{CertName}/ — cert folders (VMF, VMDR)
- ingestion/ — parse_md.py, scrape_urls.py, embed_and_store.py
- retrieval/ — retriever.py
- agent/ — tools.py, graph.py, prompts.py, agent.py
- mcp_server/ — server.py
- ui/ — app.py (Chainlit)
- tests/ — test scripts per build day
- .env — OPENAI_API_KEY, ANTHROPIC_API_KEY, TAVILY_API_KEY (never commit)


## Cert Naming
- Folder names: VMF, VMDR (these become cert_name in all Qdrant payloads)
- Notes: vmf.md, vmdr.md → source_type: notes
- Labs: vmdr_labs.md → source_type: labs (detected by _labs in filename)
- URLs: data/urls.json at project root — NOT inside cert folders


## Qdrant Config
- Collection: qualys_notes (ONE collection, never create per-cert collections)
- Vector size: 1536 | Distance: Cosine | localhost:6333
- Payload: cert_name, source_type, source_file, h1, h2, chunk_index, text


## Chunking Rules — DO NOT CHANGE without updating this file
- Primary split: ## (H2) boundaries
- Max 800 tokens per chunk (tiktoken cl100k_base)
- Context prefix on every chunk before embedding: 'Module: {h1} | Topic: {h2} — '
- 2-sentence overlap between consecutive chunks within same H2
- store the context-prefixed text in the payload text field


## Guardrails
- ALWAYS use pathlib.Path — never os.path.join or string concatenation for paths
- ALWAYS load env vars from .env via python-dotenv — never hardcode keys
- NEVER delete the Qdrant collection without --reset flag passed explicitly
- NEVER skip verification after ingestion — always run tests/test_retrieval.py
- NEVER create a new helper function if stdlib already solves it (Ponytail rule)
- NEVER add a new dependency if an installed package already covers it
- ASK before any destructive action (dropping collections, wiping files)
- Ponytail skill is installed — apply its decision ladder before writing any new code


## Verification Protocol
1. After any ingestion change: python tests/test_retrieval.py
2. Confirm exit code 0 and scores > 0.5 for all 3 test queries
3. Confirm cert_name is correct in returned payloads


## Common Mistakes — Fix These in Code, Not in Chat
- Do not use per-cert Qdrant collections — one collection, filter by cert_name payload
- Do not chunk by fixed character count — always H2-boundary-aware
- Do not embed text without the context prefix
- Do not treat urls.json content as a separate pipeline — it uses same dict format as parse_md.py
- scrape_urls.py reads from data/urls.json at ROOT not inside cert folders
