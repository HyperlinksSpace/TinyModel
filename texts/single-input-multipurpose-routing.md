# Single-input multipurpose routing (natural language -> model functions)

This note describes how to keep **one text input** while still supporting multiple functions (`classify`, `similarity`, `retrieve`) in a predictable way.

## Short answer

Yes, you can keep one input and add a "transmitter" layer. In practice, that layer is called an **intent router** (or orchestrator): it reads the user text, decides which function to call, extracts arguments, and formats output.

## How multipurpose systems are usually built

Common architecture:

1. **Single user input**
2. **Intent detection**
3. **Argument extraction**
4. **Function execution**
5. **Response formatting**

Example:

- User text: "Compare these two headlines for similarity: ... and ..."
- Router decision: `similarity`
- Parsed args: `text_a`, `text_b`
- Runtime call: `TinyModelRuntime.similarity(text_a, text_b)`
- Output: score + short explanation

## Three implementation patterns

### Pattern A: Rule-first router (fastest and safest)

- Use explicit triggers and simple parsing:
  - "classify:", "label:", "what category" -> `classify`
  - "similarity:", "compare", "how close" -> `similarity`
  - "retrieve:", "find closest", "top matches" -> `retrieve`
- If parsing fails, ask a clarification question.

Pros:

- deterministic behavior,
- easy to debug,
- low latency and no extra model.

Cons:

- limited flexibility for ambiguous phrasing.

### Pattern B: Intent classifier + parser (balanced)

- Train a small intent classifier with labels:
  - `intent_classify`,
  - `intent_similarity`,
  - `intent_retrieve`,
  - `intent_unknown`.
- After intent prediction, run per-intent argument parsing rules.

Pros:

- better natural language coverage than pure rules,
- still controllable and auditable.

Cons:

- requires intent dataset and monitoring.

### Pattern C: LLM tool-calling router (most flexible)

- Use an LLM to output structured JSON:
  - `{ "intent": "...", "args": {...}, "confidence": ... }`
- Validate JSON against schema, then call local runtime functions.

Pros:

- handles diverse phrasing well,
- easy to extend with new tools.

Cons:

- extra cost/latency,
- must enforce strong validation and safety constraints.

## Recommended approach for this repo (MVP)

Start with **Pattern A + confidence fallback**:

1. Add one function `route_query(user_text)` in Space app code.
2. Detect intent with rule set first.
3. Parse arguments by strict templates.
4. If unclear, return "I can do classify/similarity/retrieve. Please use one of these formats..."
5. Log routed intent and parse success rate for iterative improvement.

After enough usage logs, upgrade to Pattern B.

## Input contract for one-box UX

Define simple user-friendly command shapes:

- `classify: <text>`
- `similarity: <text A> || <text B>`
- `retrieve: <query> || <candidate 1> | <candidate 2> | <candidate 3>`

Why this works:

- still one input box,
- supports natural language around the command,
- makes parsing reliable.

## Ambiguity handling rules (important)

When router confidence is low:

1. Do not guess silently.
2. Ask one short clarification:
   - "Do you want classification, similarity, or retrieval?"
3. Offer examples in-place.

This prevents incorrect function calls that look "intelligent" but are wrong.

## Minimal pseudo-flow

```text
user_input
  -> detect_intent()
      -> unknown -> ask_clarification()
      -> classify -> parse_classify_args() -> runtime.classify()
      -> similarity -> parse_similarity_args() -> runtime.similarity()
      -> retrieve -> parse_retrieve_args() -> runtime.retrieve()
  -> format_response()
```

## What this means for your Space

You can keep **one input field** and still expose all features:

- route query to one of three runtime functions,
- show function-specific output block,
- keep UI simple for end users.

This is the standard multipurpose pattern in production assistants: **single entry, internal routing, strict execution contracts**.
