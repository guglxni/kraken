# FOSS Research — KRAKEN Enhancement Libraries

> Researched May 28, 2026. All libraries evaluated for license compatibility (MIT/Apache 2.0/BSD), activity (commits in 2025-2026), and direct applicability to KRAKEN's stack.

---

## Priority 1 — Adopt Immediately (high impact, low integration effort)

### 1. mem0 — Universal Memory Layer for AI Agents
- **GitHub:** https://github.com/mem0ai/mem0
- **Stars:** ~37,000
- **License:** Apache 2.0
- **What it is:** Tri-store memory layer combining vector (semantic), graph (relational), and key-value (fast recall) stores. Handles memory extraction, deduplication, contradiction resolution, and retrieval via a clean Python API.
- **Why KRAKEN needs it:** KRAKEN's `kraken/reef_memory.py` (LanceDB vector search over past voyages) is a hand-rolled approximation of exactly what mem0 provides. mem0 replaces the bespoke LanceDB wrapper while keeping LanceDB as the underlying vector store.
- **Integration:** Replace internals of `kraken/reef_memory.py`. Call `memory.add(voyage_result, user_id=voyage_id)` after each voyage, `memory.search(query)` in Quartermaster routing for few-shot exemplar injection.

---

### 2. SQLGlot — SQL Parser, Transpiler, and Lineage Extractor
- **GitHub:** https://github.com/tobymao/sqlglot
- **Stars:** ~9,200
- **License:** MIT
- **What it is:** Zero-dependency pure-Python SQL parser, formatter, transpiler, and AST-based column lineage extractor.
- **Why KRAKEN needs it:** (1) Validates voyage SQL against DuckDB dialect before runtime. (2) `sqlglot.lineage.lineage()` auto-generates the Spyglass trace view showing which Coral source contributed which column. (3) Enforces the "one clause per line" formatting convention at CI time. (4) Powers `kraken voyage:lint` with unused JOIN detection and expensive scan warnings.
- **Integration:** Add to `kraken/` as voyage compiler + pre-submit validator. Wire `sqlglot.lineage` output into `ui/app/spyglass/` backend for column-level provenance. Use `sqlglot.parse_one(sql).sql(dialect='duckdb', pretty=True)` in `kraken/voyages/compiler.py`.

---

### 3. react-force-graph — Force-Directed Graph for React
- **GitHub:** https://github.com/vasturiano/react-force-graph
- **Stars:** ~3,100
- **License:** MIT
- **What it is:** WebGL-accelerated force-directed graph renderer as a React component. Supports 2D and 3D, real-time node/link updates, and handles 10,000+ nodes.
- **Why KRAKEN needs it:** React Flow (already in plan) is excellent for structured DAGs. For the Reef Map's free-form causal graph (deploy → PR → CVE → customer ticket → Sentry error — all emerging dynamically), force-directed layout renders emergent clustering far more naturally. Supports `<800ms` first-paint target via WebGL canvas.
- **Integration:** Use `react-force-graph-2d` for `ui/app/reef-map/`. Feed from Supabase Realtime subscription streaming `kraken.findings` as graph delta events (add node, add edge). Keep React Flow for Voyage Studio structured DAG view. Switch to react-force-graph for live causal graph.

---

### 4. SQLLineage — Column-Level SQL Lineage
- **GitHub:** https://github.com/reata/sqllineage
- **Stars:** ~1,600
- **License:** MIT
- **What it is:** Takes a SQL command, produces table-level and column-level lineage as a directed graph using networkx. Can export as JSON for frontend consumption.
- **Why KRAKEN needs it:** Powers the "Spyglass shows the receipts" narrative. After each `coral_sql()` call, passes the rendered SQL through `LineageRunner` to produce a node/edge list that Spyglass renders as column provenance. Closes the loop between "what SQL ran" and "where did each result column come from."
- **Integration:** In `kraken/crew.py`, after each voyage execution, pass rendered SQL to `sqllineage.runner.LineageRunner`. Serialize `LineageResult` as node/edge JSON, write to Supabase table, subscribe via Realtime in Spyglass.

---

### 5. rich — Beautiful Terminal Output
- **GitHub:** https://github.com/Textualize/rich
- **Stars:** ~48,000
- **License:** MIT
- **What it is:** Python library for rich text and beautiful formatting in the terminal.
- **Why KRAKEN needs it:** The `kraken` CLI (`kraken/cli.py`) needs to look polished during the demo. Rich provides progress bars, syntax-highlighted SQL output, tables, panels, and spinners — all zero-config.
- **Integration:** Replace all `print()` calls in CLI with `rich.console.Console()`. Use `rich.progress.Progress` for voyage execution, `rich.syntax.Syntax` for SQL output, `rich.table.Table` for findings display.

---

### 6. fastembed — Local Embeddings (No API)
- **GitHub:** https://github.com/qdrant/fastembed
- **Stars:** ~1,500
- **License:** Apache 2.0
- **What it is:** Lightweight, fast Python library for generating text embeddings locally using ONNX Runtime. No API calls, no GPU required.
- **Why KRAKEN needs it:** Reef Memory needs to embed voyage SQL + outcomes for similarity search. fastembed runs fully local (no API cost, no data egress — aligns with KRAKEN's local-first promise), and is fast enough for real-time voyage embedding on an M3 Pro.
- **Integration:** Use in `kraken/reef_memory.py` (or mem0's vector store config) as the embedding function. `TextEmbedding("BAAI/bge-small-en-v1.5")` is 130MB and runs in ~10ms per embed.

---

## Priority 2 — Add for Demo Polish

### 7. Marquez — OpenLineage Reference Implementation
- **GitHub:** https://github.com/MarquezProject/marquez
- **Stars:** ~2,100
- **License:** Apache 2.0
- **What it is:** LF AI & Data metadata server implementing OpenLineage. REST API, lineage graph UI, connectors for dbt/Airflow/Spark.
- **Why KRAKEN needs it:** Each voyage run's input/output Coral tables become OpenLineage Dataset entities, giving a queryable audit trail of "which voyage touched which source, when." Directly supports the "Spyglass shows the receipts" narrative and the Crow's Nest trace view.
- **Integration:** Add to `infra/docker-compose.yaml`. Emit OpenLineage events from `kraken/coral_client.py` after every `coral_sql()` call via `openlineage-python` client. `voyage_id` → Marquez Run, each Coral source table → Dataset.

---

### 8. Laminar — Agent Observability (Multi-agent workflows)
- **GitHub:** https://github.com/lmnr-ai/lmnr
- **Stars:** ~2,800
- **License:** Apache 2.0
- **What it is:** OpenTelemetry-native observability purpose-built for long-running multi-agent workflows. Auto-instruments Anthropic SDK calls. Has a swimlane agent-timeline UI.
- **Why KRAKEN needs it:** Langfuse (already in plan) is prompt-centric. Laminar's swimlane view per agent is stronger for visualizing the 6-agent KRAKEN swarm. Can run as a secondary trace sink alongside Langfuse via OTel multi-exporter.
- **Integration:** Add `OTEL_EXPORTER_OTLP_ENDPOINT` multi-target config in `kraken/`. Laminar's swimlane view makes the Crow's Nest panel more compelling for the demo.

---

### 9. Opik by Comet — LLM Evaluation Harness
- **GitHub:** https://github.com/comet-ml/opik
- **Stars:** 4,000+
- **License:** Apache 2.0
- **What it is:** Open-source LLM evaluation: LLM-as-judge, prompt experiments, dataset management. Claims 40M+ traces/day in production.
- **Why KRAKEN needs it:** Bench-O-Bot (`kraken/bench.py`) needs to produce a quantitative "Coral wins by X%" result. Opik's LLM-as-judge scoring records each Coral SQL voyage run vs. direct-MCP equivalent as an experiment with structured input/output and automatic scoring.
- **Integration:** Use Opik SDK in `kraken/bench.py`. Each bench run becomes an Opik experiment. Results feed the Bench-O-Bot side-by-side panel in Spyglass.

---

### 10. react-querybuilder — Visual WHERE Clause Builder
- **GitHub:** https://github.com/react-querybuilder/react-querybuilder
- **Stars:** ~1,600
- **License:** MIT
- **What it is:** TypeScript-first visual query builder for React. Exports SQL WHERE clauses, supports drag-and-drop field composition, has `@react-querybuilder/dnd` add-on. Compatible with shadcn/ui via `controlElements` prop.
- **Why KRAKEN needs it:** Voyage Studio's WHERE clause composer. Instead of writing raw SQL predicates, users visually compose filter conditions on voyage parameters (e.g., "hours_back > 24", "severity >= 7.0").
- **Integration:** In `ui/app/voyage-studio/`, use `QueryBuilder` for WHERE clause composition. Serialize via `formatQuery(query, 'json_without_ids')`, merge into Jinja2 voyage YAML template via SQLGlot at render time.

---

## Priority 3 — Infrastructure & Schema Intelligence

### 11. OpenMetadata — Metadata Knowledge Graph
- **GitHub:** https://github.com/open-metadata/OpenMetadata
- **Stars:** ~13,500
- **License:** Apache 2.0
- **What it is:** 120+ connectors, column-level lineage, unified metadata knowledge graph, MCP server. Semantic search and glossary for governed vocabulary.
- **Why KRAKEN needs it:** Understands that `github.pull_requests.merged_by` and `linear.issues.assignee` refer to the same concept. Schema discovery for Voyage Studio auto-complete and foreign key suggestions. MCP server means agents can query metadata without violating Rule 1.
- **Integration:** Add to `infra/docker-compose.yaml`. Register KRAKEN's Coral source schemas on first boot. Use OpenMetadata's MCP server for schema discovery in Voyage Studio.
- **Caveat:** Heavy service — only add if docker compose time stays <60s.

---

### 12. Python Record Linkage Toolkit
- **GitHub:** https://github.com/J535D165/recordlinkage
- **Stars:** ~500 (well-established, high PyPI downloads)
- **License:** BSD 3-Clause
- **What it is:** Probabilistic entity matching across heterogeneous data sources. Blocking indexes, string/numeric comparison functions.
- **Why KRAKEN needs it:** Cross-source JOINs (e.g., `github.author_email` vs `stripe.customer_email`) often have no guaranteed foreign key. Record Linkage Toolkit resolves them probabilistically, writing match scores back to `kraken.findings` as an `entity_links` table that voyages can JOIN against.
- **Integration:** Pre-processing step in `kraken/blackboard.py` when Quartermaster prepares a voyage plan. Match probabilities written to `kraken.findings` as structured findings.

---

### 13. reagraph — WebGL Network Graph (Alternative Reef Map)
- **GitHub:** https://github.com/reaviz/reagraph
- **Stars:** ~931
- **License:** Apache 2.0
- **What it is:** Declarative `GraphCanvas` React component with node clustering, label rendering, and `useGraphLayout` hook for switching between force-directed and hierarchical layouts at runtime.
- **Why KRAKEN needs it:** Alternative to `react-force-graph` if a more declarative, component-library-style API is preferred. Use one, not both.
- **Integration:** Swap for `react-force-graph-2d` in `ui/app/reef-map/` if the imperative ref API of react-force-graph is problematic.

---

## Rejected Libraries (and why)

| Library | Reason Rejected |
|---|---|
| `react-awesome-query-builder` | Maintainers flagged as low-activity, no npm releases in 12 months |
| LangChain | CLAUDE.md explicitly forbids it |
| LangGraph | CLAUDE.md explicitly forbids it |
| OpenClaw/NullClaw/ZeroClaw | CLAUDE.md explicitly forbids any "claw" framework runtime |
| gitclaw runtime | gitagent is a file format only; CLAUDE.md forbids the runtime |
| Celery/Sidekiq | CLAUDE.md explicitly forbids; Trigger.dev handles scheduling |
| Redis | CLAUDE.md explicitly forbids; Supabase Realtime covers messaging |
| Apollo/urql | CLAUDE.md forbids GraphQL clients in agent layer |
| SQLAlchemy/Prisma/Drizzle | CLAUDE.md forbids generic ORMs for agent data access |

---

## Adoption Summary by Component

| KRAKEN Component | FOSS Library to Add |
|---|---|
| `kraken/reef_memory.py` | mem0 + fastembed |
| `kraken/voyages/compiler.py` | SQLGlot |
| `kraken/bench.py` | Opik |
| `kraken/crew.py` | SQLLineage (post-SQL lineage emit) |
| `kraken/cli.py` | rich |
| `ui/app/reef-map/` | react-force-graph-2d |
| `ui/app/voyage-studio/` | react-querybuilder |
| `infra/docker-compose.yaml` | Marquez (OpenLineage) + Laminar |
| `kraken/blackboard.py` | Python Record Linkage Toolkit (entity resolution) |

---

## Sources

- [mem0 — mem0ai/mem0](https://github.com/mem0ai/mem0)
- [SQLGlot — tobymao/sqlglot](https://github.com/tobymao/sqlglot)
- [react-force-graph — vasturiano/react-force-graph](https://github.com/vasturiano/react-force-graph)
- [SQLLineage — reata/sqllineage](https://github.com/reata/sqllineage)
- [rich — Textualize/rich](https://github.com/Textualize/rich)
- [fastembed — qdrant/fastembed](https://github.com/qdrant/fastembed)
- [Marquez — MarquezProject/marquez](https://github.com/MarquezProject/marquez)
- [Laminar — lmnr-ai/lmnr](https://github.com/lmnr-ai/lmnr)
- [Opik — comet-ml/opik](https://github.com/comet-ml/opik)
- [react-querybuilder — react-querybuilder/react-querybuilder](https://github.com/react-querybuilder/react-querybuilder)
- [OpenMetadata — open-metadata/OpenMetadata](https://github.com/open-metadata/OpenMetadata)
- [Python Record Linkage Toolkit — J535D165/recordlinkage](https://github.com/J535D165/recordlinkage)
- [reagraph — reaviz/reagraph](https://github.com/reaviz/reagraph)
