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

## Agent Architecture (added Day 4)
- Framework: LangGraph with SqliteSaver checkpointer
- State schema: AgentState TypedDict in agent/graph.py
- State fields: messages (list), tool_called (str), context (str), session_id (str), cert_filter (str|None)
- Nodes: classify_intent, search_notes, quiz_me, suggest_workflow, web_search, generate_response
- Fallback edge: search_notes → web_search if all scores < 0.5
- Memory: SqliteSaver at data/memory.db — thread_id = Chainlit session UUID
- Entry point: agent/agent.py exposes run() and astream_events()
- Tools import from: agent/tools.py (search_notes, quiz_me, suggest_workflow, web_search)
- Retriever import from: retrieval/retriever.py (Retriever class)


## Interface Config (added Day 5)
- Chainlit UI: ui/app.py — localhost:8000 — chainlit run ui\app.py
- MCP server: mcp_server/server.py — stdio transport — FastMCP
- Claude Desktop config: %APPDATA%\Claude\claude_desktop_config.json
- Windows MCP path: use double-backslash or forward-slash — never single backslash
- Session memory: data/memory.db (SQLite) — do not delete this file during testing


## Subagents (added Days 4-6)
- routing-reviewer: reviews intent classification mistakes — invoke when wrong tool fires
- eval-runner: runs test scripts and reports results — never modifies code


## Pending — environment migration cleanup
- Project moved to C:\Users\gonis\OneDrive\Documents\Projects\QualysGPT. MCP integration is BROKEN until fixed:
  - Update absolute paths in .mcp.json (Claude Code) and mcp_server/manifest.json (venv python + server.py) to the new root
  - Re-run `mcpb pack`, uninstall the old QualysGPT extension in Claude Desktop (Settings > Extensions), install the new .mcpb
  - Verify: /mcp in Claude Code shows 4 tools; one qualys_search_notes call in Claude Desktop
- OneDrive risk: exclude this folder from OneDrive sync (or move project out of OneDrive) — sync file-locking can corrupt data/memory.db, data/chainlit.db, and storage/ during live Chainlit/Qdrant sessions
- If the folder was copied (not a fresh clone), recreate the venv: python -m venv venv + pip install -r requirements.txt (old venv has C:\Users\i\... baked in)