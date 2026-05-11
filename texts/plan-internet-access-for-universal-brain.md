# Plan: giving Universal Brain access to the open web

This document outlines a **practical** path to let the chat stack (see [`universal-brain-current-state-features-and-testing.md`](universal-brain-current-state-features-and-testing.md)) use **current information from the internet**. It is **not** a plan to download or index the entire web (infeasible); it is a plan for **bounded, policy-controlled web access** that *behaves* like “the model can use the internet” from a user perspective.

Related design context: intent routing and tool extension in [`single-input-multipurpose-routing.md`](single-input-multipurpose-routing.md).

---

## 1) Clarify the product goal

| User phrase | Engineering meaning |
| ------------- | ------------------- |
| “Access the whole internet” | Ability to **discover and fetch** arbitrary public URLs or **query search engines / news APIs**, then **ground** answers in retrieved text. |
| What we do **not** mean | Storing a full copy of the web, real-time crawl of “everything,” or bypassing robots, paywalls, or auth. |

Success looks like: **verifiable citations**, **fresh facts when needed**, **safe failure modes** (timeouts, blocked hosts, empty results), and **predictable cost**.

---

## 2) High-level architecture

Use a **tool-using agent loop** (already aligned with JSON routing + slash tools in `universal_brain_chat.py`):

1. **Router** adds an intent such as `web_search` or `fetch_url` (or a single `web` intent with a sub-action).
2. **Tool layer** runs **outside** the generative model: HTTP client, search API client, optional HTML-to-text extractor.
3. **Context builder** merges **trimmed, attributed** snippets into the prompt (same pattern as FAQ RAG today).
4. **Model** answers **only from provided snippets** when the user asked for live web grounding; otherwise normal chat.

Optional: a second pass that asks the model to **list which claims** are from web vs. from parametric knowledge.

---

## 3) Implementation options (pick one primary + optional fallback)

### Option A — Search API (recommended first)

- Integrate **one** search provider; see **§4** for a **pricing and open-source survey** (Brave, SerpApi, Tavily, Exa, Bing, Google legacy, SearXNG, etc.).
- **Pros:** Legitimate ToS, structured snippets, less parsing than raw HTML.
- **Cons:** API keys, quotas, ongoing cost.

**Milestone:** `web_search <query>` returns titles, URLs, and snippet text; router maps “what’s the latest on …” to this tool.

### Option B — Fetch URL + readability extraction

- Given an allowlisted fetch, `GET` the page, extract main text (readability / trafilatura / boilerplate removal).
- **Pros:** Deep pages when the user pastes a link.
- **Cons:** SSRF risk, heavy pages, legal/ToS per site, need size/time limits.

**Milestone:** `/fetch https://example.com/path` or router intent `fetch_url` with URL validation.

### Option C — Browser automation (later / niche)

- Headless browser for JS-heavy sites.
- **Pros:** Renders dynamic content.
- **Cons:** Slow, expensive, fragile on Hugging Face Spaces; better as a **self-hosted** profile.

### Option D — Curated connectors

- Wikipedia API, official docs, RSS, government open data.
- **Pros:** Stable, cacheable, fewer legal gray areas.
- **Cons:** Not “whole internet,” but high signal for many queries.

**Recommendation:** Ship **A + B (strictly gated)** first; add **D** where it matches product vertical.

---

## 4) Search provider research (pricing, free tiers, open source)

**Currency:** USD unless noted. **Important:** plans and quotas change frequently—use this section for **orientation**, then confirm on each vendor’s **official pricing / ToS** page before you commit.

### 4.1 Commercial “search-as-a-service” APIs

| Provider | Free or entry tier (verify live) | Typical paid shape | Notes |
| -------- | -------------------------------- | ------------------ | ----- |
| **[Brave Search API](https://api.brave.com/)** | Historically included monthly free/query credits; **Brave has moved toward metered billing**—check [plans dashboard](https://api-dashboard.search.brave.com/app/plans). | Order of **~$5 / 1,000 web searches** (tiered product lines: web, answers, spellcheck, etc.). | Strong fit for AI/RAG snippets; watch attribution requirements. |
| **[SerpApi](https://serpapi.com/pricing)** | **~100 searches/month** on free tier (signup). | **~$25/mo** for on the order of **1k** searches/month on entry paid tiers; higher tiers reduce per-search cost. | Returns structured Google (and other engine) SERPs; “Legal Shield” on some paid tiers—read their terms. |
| **[Tavily](https://www.tavily.com/pricing)** | **Researcher** tier: on the order of **~1,000 API credits/month** free (credit-card rules vary). | Paid tiers from **~$30/mo** upward with more credits; extract/search operations burn credits at different rates ([docs](https://docs.tavily.com/documentation/api-credits)). | Designed for LLM/tool use; good default for prototypes. |
| **[Exa](https://exa.ai/pricing)** | On the order of **~1,000 requests/month** free for API usage (verify). | Search roughly **~$7 / 1,000** requests for standard search (bundling/pricing updated over time); “deep” endpoints cost more. | Neural/semantic search angle; startup/education grants sometimes available. |
| **[Google Custom Search JSON API](https://developers.google.com/custom-search/v1/overview)** | **Not available to new customers** (as of Google’s published notice). Existing customers: historically **100 queries/day** free, then **$5 / 1,000** queries (caps apply); **service discontinuation Jan 1, 2027** for remaining users. | Google steers new workloads to **[Vertex AI Search](https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-vertex-ai-search)** and related (separate Cloud pricing). | Do **not** plan net-new products on Custom Search JSON API. |
| **[Bing Web Search API](https://learn.microsoft.com/en-us/bing/search-apis/bing-web-search/overview)** (via Azure / Microsoft) | Microsoft has advertised a **limited free tier** on certain Bing Search resource SKUs (confirm in the **current** [Bing Search API pricing](https://www.microsoft.com/en-us/bing/apis/pricing) and Azure portal). | Often cited in the **~$15–$25 / 1,000 transactions** range depending on tier and bundle—**must verify** for your region and API version. | Enterprise-friendly; good if you already bill Azure. |

**Also-rans / patterns:** many “SERP scraper” APIs exist (e.g. ScrapingBee, ScrapingDog); compare **legitimacy, latency, and legal exposure** the same way you would SerpApi.

### 4.2 Open-source and no-per-query-vendor-fee options

These avoid paying a search vendor **per query**, but **are not “free” in ops**: you run infrastructure, handle abuse, and must still respect **upstream search engines’ terms** when you proxy them.

| Option | What it is | License | Typical use | Caveats |
| ------ | ----------- | ------- | ----------- | ------- |
| **[SearXNG](https://github.com/searxng/searxng)** | Self-hosted **metasearch** (aggregates configurable backends). | **AGPL-3.0** | Private relay: your Universal Brain backend calls **your** SearXNG instance. | Each enabled backend may forbid automated access; rate limits; **public** SearXNG instances are **not** reliable for production. |
| **[YaCy](https://github.com/yacy/yacy_search_server)** | Decentralized search node / crawler. | **GPL-2.0** | Research or intranet-style deployments. | Heavy ops; different freshness/trust model than Bing/Google APIs. |
| **Wikipedia / Wikidata APIs** | Structured, license-friendly **knowledge** APIs. | Content under **CC BY-SA** (attribution required). | Great for factual grounding where an article exists. | Not a substitute for arbitrary web search. |
| **RSS/Atom + official feeds** | Poll **publisher feeds** you allowlist. | Varies by source. | News/product updates without scraping HTML. | Coverage is whatever you configure. |
| **Common Crawl, WARC dumps** | Open **snapshots** of the web. | Open data terms per dataset. | Offline RAG, batch research—not live “today’s headline” search. | Storage and indexing cost dominates. |

**Not recommended without legal review:** “Google front-end” proxies (**Whoogle**, etc.) and scripts that **scrape** consumer search UIs (e.g. DuckDuckGo HTML). They often conflict with **site ToS** and are a poor fit for **Hugging Face Spaces** or commercial products.

### 4.3 Practical picks for this repository

- **Smallest integration friction (hosted):** Tavily, SerpApi (low free tier), or Exa (free tier)—all expose HTTP APIs suited to a Python tool in `universal_brain_chat.py`.
- **Lowest marginal API cost:** self-hosted **SearXNG** with a **small allowlist** of backends you are allowed to automate—or skip generic web search and use **Wikipedia + curated RSS + URL fetch (§3 Option B)**.
- **Enterprise / Azure shop:** Bing Web Search via Azure, with budgets tied to transaction counts.

### 4.4 Google Custom Search JSON API — instruction check, implementation plan, env, Hugging Face

This subsection maps the **Programmable Search Engine + JSON API** flow (the Russian/English intro you followed) to **this repo’s Universal Brain** and clarifies **who calls whom** on Hugging Face.

#### A) Is the instruction accurate?

Yes, for **mechanics** (see [Custom Search JSON API overview](https://developers.google.com/custom-search/v1/overview)):

| Instruction claim | Correct? |
| ----------------- | -------- |
| You must **create a Programmable Search Engine** first; API queries hit **that** engine instance. | Yes. |
| **Search engine ID** = parameter **`cx`** (shown under engine basics / overview in the [control panel](https://programmablesearchengine.google.com/controlpanel/all)). | Yes. |
| You need a **Google API key** and pass **`key=...`** on requests. | Yes. |
| The API exposes essentially one read operation: **`cse.list`** → **HTTP GET** returning JSON (metadata + `items` results). | Yes. |
| Custom OpenSearch-related fields include **`cx`**, **`safe`** (safe search level), and link relations for **next/previous** page. | Yes (see [REST / response](https://developers.google.com/custom-search/v1/using_rest)). |

**Critical caveat (product, not tutorial):** Google states the **Custom Search JSON API is closed to new customers**; existing customers must migrate before **2027-01-01**. If your GCP project **cannot** enable `customsearch.googleapis.com` or the console blocks new PSE+JSON usage, stop planning on this API and use **Vertex AI Search** or another provider from §4.1.

**Security caveat:** The doc line that the key is “safe in URLs” applies to **transport encoding**, not **secrecy**. On a **public Space**, treat **`key` as a secret**: never put it in Gradio client code, never commit it; restrict the key in **Google Cloud Console** (API key restrictions: limit to **Custom Search API** only; avoid browser-referrer-only restrictions for server-side Spaces).

#### B) Implementation plan (this repository)

| Step | Work |
| ---- | ---- |
| **1. Google side** | Create a **Programmable Search Engine**, note **`cx`**. In [Google Cloud Console](https://console.cloud.google.com/) enable **Custom Search API** (if still allowed for your account), attach **billing** for paid quota beyond the free daily allowance. Create an **API key** with restrictions limited to Custom Search API. |
| **2. Python client module** | Add a small module (e.g. `scripts/google_cse_client.py`) that performs **GET** `https://www.googleapis.com/customsearch/v1` with query params `key`, `cx`, `q`, and optional `safe`, `num` (≤ 10), `start` (pagination), `lr` / `gl` if you need locale. Parse `items[]` → list of `{title, link, snippet}`; cap total characters for the LM context. |
| **3. Universal Brain wiring** | In `universal_brain_chat.py`: if env is set, register a **`web_search`** path in `run_routed_tool` (and/or `handle_slash` for `/web <query>`). Build a **single text block** of numbered excerpts with URLs (same spirit as FAQ RAG). Append to system/extras before `generate_chat_reply`. Add **brain trace** token e.g. `web:CSE:n`. |
| **4. Router** | Extend `ROUTER_SYSTEM` with intent `web_search` (or reuse a generic name) so NL “search the web for …” maps to the tool when enabled. |
| **5. Rate limits & cache** | Enforce per-session cooldown + optional in-memory LRU by query hash to reduce duplicate billing. |
| **6. Tests** | Mock `httpx`/`requests` responses; assert no key in logs; assert empty `items` is handled. |
| **7. Docs** | Space README: “Requires secrets `…`”; link to Google attribution / PSE terms if you show results publicly. |

#### C) Environment variables to provide

Use names you control; these are conventional:

| Variable | Required | Secret? | Purpose |
| -------- | -------- | ------- | -------- |
| **`GOOGLE_CSE_API_KEY`** | Yes, for CSE search | **Yes** | Value of `key=` passed to Google’s REST endpoint. |
| **`GOOGLE_CSE_CX`** | Yes | Usually **no** (it is an engine id, not a password) | Programmable Search Engine id = `cx`. |
| **`GOOGLE_CSE_SAFE`** | No | No | Maps to Google’s `safe` query param; allowed strings are defined in the official [`cse.list`](https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list) reference (e.g. **`off`**, **`active`**). |
| **`GOOGLE_CSE_NUM`** | No | No | Results per request; integer **1–10** (API limit per call). |
| **`GOOGLE_CSE_ENABLE`** | No | No | Feature flag `1`/`true` so local dev can omit Google without errors. |

Optional later: **`GOOGLE_CSE_GL`**, **`GOOGLE_CSE_CR`**, **`GOOGLE_CSE_LR`** for region/language bias (see `cse.list` reference).

**Hugging Face Space:** add **`GOOGLE_CSE_API_KEY`** under the Space’s **Settings → Secrets** (masked). Add **`GOOGLE_CSE_CX`** (and optional vars) under **Settings → Variables** if you prefer them visible to collaborators, or secrets if you treat `cx` as sensitive.

**Local:** same variables in `.env` or your shell; never commit.

#### D) How Hugging Face Space and “Hugging Face” access Google

Important distinction:

1. **Hugging Face (the platform)** does **not** proxy your search. The **Space container** (your `app.py` → `universal_brain_chat.py`) runs **your** code.
2. **Access path:**  
   **User browser** → **HTTPS** → **Gradio app on the Space** (HF hosts the machine) → **your Python** issues **outbound HTTPS GET** → **`www.googleapis.com`** (Google).  
   The **API key never goes to the user’s browser** if you only call Google from the server process.
3. **Secrets injection:** At Space startup, HF injects repository **Secrets/Variables** as **environment variables** into the container. Your code reads `os.environ["GOOGLE_CSE_API_KEY"]` and builds the Google URL **server-side only**.
4. **Network:** Spaces generally allow outbound internet; if a corporate mirror blocks Google, searches fail until egress allows **`https://www.googleapis.com/`** (confirm in Space logs).

**Summary:** “Hugging Face accesses Google” is shorthand for **your Space backend** calling Google with **your** key; HF stores the secret and provides the runtime.

---

## 5) Safety and abuse (non-optional)

### 5.1 Network and SSRF

- **Allowlist** schemes (`https` only by default).
- **Block** private IPs, localhost, cloud metadata IPs, link-local, and non-standard ports.
- **Cap** response size (e.g. first N MB) and **time** (connect + read timeouts).
- **Redirect** policy: limit hops; strip credentials in URLs.

### 5.2 Content and policy

- Strip scripts; store **text only** in context.
- Optional **content filter** on snippets before they enter the model (PII regex, NSFW classifiers) if product requires it.
- **Rate limit** per session / IP / API key.

### 5.3 Honesty and citations

- Require **inline citations** mapping claims to `(url, excerpt_id)` in the user-visible answer.
- If retrieval is empty or low-quality, answer must say so and avoid fabrication.

### 5.4 Secrets

- Search API keys live in **environment / Space secrets**, never in the repo or client bundle.

---

## 6) Integration with the existing Universal Brain stack

### 6.1 Router schema

Extend the router JSON schema (see `ROUTER_SYSTEM` in `scripts/universal_brain_chat.py`) with intents such as:

- `web_search` — `text` = query string.
- `fetch_url` — `text` = single URL (or structured field `url` if you refactor the schema).

Validate outputs; on validation failure, fall back to `chat` with a short clarification.

### 6.2 Slash commands (parity with FAQ tools)

Add shortcuts, for example:

- `/web <query>` or `/search <query>`
- `/fetch <url>` (if enabled)

This gives deterministic testing without relying on NL routing.

### 6.3 Memory and RAG interaction

- **Default:** web snippets are **ephemeral** for that turn (or short TTL cache), not auto-written to long-term memory unless the user uses `/remember`.
- **Conflict policy:** if FAQ corpus and web disagree, prefer **user-visible disclaimer** and cite both sources.

### 6.4 Brain trace

- Extend the trace line with e.g. `web:2hits` or `fetch:example.com` for operators (same pattern as `RAG:` / `classify:`).

---

## 7) Hugging Face Spaces constraints

- **Outbound HTTP:** usually allowed; confirm current Space runtime policy and document required domains for the search provider.
- **Cold start + latency:** web tools add seconds; use **async queue** and show “searching…” in UI if you add status components later.
- **ToS:** HF and the search vendor must permit the use case; read **API license** and **attribution** requirements (some APIs require logo or text attribution in the UI).
- **GPU vs CPU:** web I/O is CPU-bound; no need for GPU for the fetch layer.

If a Space cannot meet compliance, offer the same code path **self-hosted** with API keys.

---

## 8) Phased rollout

| Phase | Deliverable | Exit criteria |
| ----- | ----------- | ------------- |
| **0** | Threat model + allowlist spec | Document signed off internally |
| **1** | Search API tool + `/web` + router intent | 20 golden queries return cited answers |
| **2** | URL fetch + extraction (gated) | SSRF tests pass; size/time caps enforced |
| **3** | Caching + deduplication | Duplicate queries don’t double-bill API |
| **4** | UI: citations panel or footnotes | Users can open sources in one click |
| **5** | Evaluation harness | Compare grounded vs. ungrounded on dated facts |

---

## 9) Evaluation (how you know it works)

- **Golden set:** questions with **known recent answers** (sports scores, release dates, “who is CEO of X” with controlled dates).
- **Ablation:** with web tool off, model should **refuse or hedge** on time-sensitive facts if you configure strict mode.
- **Safety tests:** internal URLs, `file://`, redirects to metadata endpoints must **fail closed**.
- **Latency SLO:** p95 end-to-end under a budget you set for the product tier.

---

## 10) Open decisions (record answers as you go)

1. **Single vendor vs. fallback** search provider.
2. **Languages** and locale bias of search results.
3. **Paying** for API vs. sponsoring only free tiers on Hub.
4. Whether **fetch_url** is enabled on the **public** Space or only in **private** deployments.
5. **Logging:** whether to store queries/URLs (privacy impact).

---

## 11) Summary

“Whole internet” capability is implemented as **search + optional bounded fetch**, wired as **validated tools** in front of the existing RAG-style context injection, with **citations**, **SSRF controls**, and **clear Hugging Face / API compliance**. The Universal Brain codebase already has the right seams (router, slash commands, trace, FAQ RAG); this plan extends those seams without requiring a new model architecture.
