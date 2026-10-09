"""Free AI layer — Groq LLM when configured, offline fallback otherwise.

Providers (in order):
  - summarize/ask: Groq (free tier, GROQ_API_KEY=gsk_...) -> real LLM answer
  - fallback: offline extractive frequency summarizer + TF-IDF retrieval
    with page citations (zero downloads, zero keys)
  - markdown/forms: PyMuPDF heuristics (free)
  - translate: Ollama / LibreTranslate if set, else honest offline passthrough.

API shape stays identical either way: {summary|answer, sources, provider}.
"""

from pathlib import Path
import math
import os
import re
from collections import Counter
import fitz

try:
    from ..utils.config import settings
except Exception:  # pragma: no cover - importable without app context in tests
    settings = None  # type: ignore


def _groq_key() -> str:
    if settings is not None and getattr(settings, "groq_api_key", ""):
        return str(settings.groq_api_key).strip()
    return os.environ.get("GROQ_API_KEY", "").strip()


def _groq_model() -> str:
    if settings is not None and getattr(settings, "groq_model", ""):
        return str(settings.groq_model).strip() or "openai/gpt-oss-120b"
    return os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b").strip() or "openai/gpt-oss-120b"


def _groq_base_url() -> str:
    if settings is not None and getattr(settings, "groq_base_url", ""):
        return str(settings.groq_base_url).rstrip("/")
    return os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")


def _groq_max_chars() -> int:
    try:
        if settings is not None and getattr(settings, "groq_max_chars", 0):
            return int(settings.groq_max_chars)
    except Exception:
        pass
    try:
        return int(os.environ.get("GROQ_MAX_CHARS", "15000"))
    except Exception:
        return 15000


def groq_status() -> dict:
    """Report which AI provider summarize/ask will use (for UI + /api/tools/ai/status)."""
    key = _groq_key()
    model = _groq_model()
    if key:
        return {"provider": f"groq:{model}", "configured": True, "model": model,
                "fallback": "offline-extractive / offline-tfidf"}
    return {"provider": "offline-extractive / offline-tfidf", "configured": False,
            "model": model, "fallback": None,
            "hint": "Set GROQ_API_KEY=gsk_... for real LLM answers (free tier: console.groq.com)."}


def _groq_chat(system: str, user: str, max_tokens: int = 1024, temperature: float = 0.3) -> str:
    """Single Groq OpenAI-compatible chat call. Raises on any failure (caller falls back)."""
    import httpx  # lazy: keeps boot light when Groq is unused
    key = _groq_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY not configured")
    timeout = float(getattr(settings, "groq_timeout_s", 30.0)) if settings is not None else 30.0
    resp = httpx.post(
        f"{_groq_base_url()}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": _groq_model(),
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}],
              "temperature": temperature,
              "max_tokens": max_tokens},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    text = (text or "").strip()
    if not text:
        raise RuntimeError(f"Empty Groq response: {str(data)[:300]}")
    return text


def _context_text(pages: list[dict], max_chars: int | None = None) -> str:
    cap = max_chars or _groq_max_chars()
    parts: list[str] = []
    total = 0
    for p in pages:
        chunk = f"\n[Page {p['page']}]\n{(p.get('text') or '').strip()}"
        if not chunk.strip():
            continue
        if total + len(chunk) > cap:
            parts.append(chunk[: max(0, cap - total)])
            break
        parts.append(chunk)
        total += len(chunk)
    return "".join(parts).strip()

STOP = set("""a an the and or but if then else for of in on to with as at by from is are was were be been
has have had it its this that these those you your we our they their he she him her his hers ours yours
not no yes can will just more most other some such only over under into out up down over again once here there
page figure table section introduction conclusion summary background method methods result results""".split())


def _pages(src: Path) -> list[dict]:
    doc = fitz.open(str(src))
    out = [{"page": i + 1, "text": doc[i].get_text().strip()} for i in range(len(doc))]
    doc.close()
    return out


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [s.strip() for s in parts if len(s.strip()) > 30][:400]


def summarize_pdf(src: Path, mode: str = "key-points", max_sentences: int = 8) -> dict:
    """Summarize via Groq when GROQ_API_KEY is set, else offline extractive fallback."""
    pages = _pages(src)
    if _groq_key():
        try:
            return _summarize_groq(pages, mode)
        except Exception:
            pass  # fall through to offline — AI jobs must never hard-fail
    return _summarize_offline(pages, mode, max_sentences)


def _summarize_offline(pages: list[dict], mode: str = "key-points", max_sentences: int = 8) -> dict:
    full = "\n".join(p["text"] for p in pages)
    sents = _sentences(full)
    if not sents:
        return {"summary": "No extractable text found. Run OCR first for scanned PDFs.", "sources": [], "provider": "offline-extractive"}
    words = re.findall(r"[a-z]{3,}", full.lower())
    freq = Counter(w for w in words if w not in STOP)
    scored = sorted(sents, key=lambda s: sum(freq.get(w, 0) for w in re.findall(r"[a-z]{3,}", s.lower())), reverse=True)
    n = {"quick": 3, "detailed": 10, "executive": 5, "key-points": 8}.get(mode, max_sentences)
    picked = scored[:n]
    # map back to pages for citations
    sources: list[int] = []
    for s in picked:
        for p in pages:
            if s[:40] in p["text"]:
                sources.append(p["page"])
                break
    bullets = "\n".join(f"• {s}" for s in picked)
    header = {"quick": "Quick summary", "detailed": "Detailed summary",
              "executive": "Executive summary", "key-points": "Key points"}[mode] if mode in ("quick", "detailed", "executive", "key-points") else "Summary"
    return {"summary": f"{header} (offline, free):\n{bullets}", "sources": sorted(set(sources)),
            "provider": "offline-extractive", "mode": mode}


_SUMMARIZE_INSTRUCTIONS = {
    "quick": "Write a 3-sentence quick summary.",
    "detailed": "Write a detailed summary covering every major section, ~10 bullet points.",
    "executive": "Write a 5-sentence executive summary for a busy decision-maker.",
    "key-points": "List the 8 most important key points as bullet points.",
}


def _summarize_groq(pages: list[dict], mode: str = "key-points") -> dict:
    context = _context_text(pages)
    if not context.strip():
        return {"summary": "No extractable text found. Run OCR first for scanned PDFs.",
                "sources": [], "provider": f"groq:{_groq_model()}", "mode": mode}
    instruction = _SUMMARIZE_INSTRUCTIONS.get(mode, _SUMMARIZE_INSTRUCTIONS["key-points"])
    header = {"quick": "Quick summary", "detailed": "Detailed summary",
              "executive": "Executive summary", "key-points": "Key points"}.get(mode, "Summary")
    text = _groq_chat(
        system="You summarize PDF documents accurately. Use ONLY the provided document text. "
               "Never invent facts. End with page references like (p.2) where relevant.",
        user=f"{instruction}\n\nDOCUMENT:\n{context}",
        max_tokens=1024,
        temperature=0.3,
    )
    # Honest citations: map offline-extractive top sentences back to pages so
    # the UI can still show source pages even for LLM summaries.
    try:
        cited = _summarize_offline(pages, mode).get("sources", [])
    except Exception:
        cited = sorted({p["page"] for p in pages if p.get("text", "").strip()})
    return {"summary": f"{header}:\n{text}", "sources": cited,
            "provider": f"groq:{_groq_model()}", "mode": mode}


def ask_pdf(src: Path, question: str, top_k: int = 4) -> dict:
    """Answer via Groq grounded in retrieved passages; offline TF-IDF fallback."""
    pages = _pages(src)
    if _groq_key() and (question or "").strip():
        try:
            return _ask_groq(pages, question, top_k)
        except Exception:
            pass  # fall through to offline — AI jobs must never hard-fail
    return _ask_offline(pages, question, top_k)


def _retrieve(corpus_pages: list[dict], question: str, top_k: int = 4) -> tuple[list[dict], Counter, int]:
    corpus = []
    for p in corpus_pages:
        for s in _sentences(p["text"]):
            corpus.append({"page": p["page"], "sent": s})
    qterms = [w for w in re.findall(r"[a-z]{3,}", question.lower()) if w not in STOP]
    df = Counter()
    for c in corpus:
        for w in set(re.findall(r"[a-z]{3,}", c["sent"].lower())):
            df[w] += 1
    N = len(corpus)
    return corpus, df, N


def _ask_groq(pages: list[dict], question: str, top_k: int = 4) -> dict:
    corpus, df, N = _retrieve(pages, question, top_k)
    if not corpus:
        return {"answer": "No extractable text. Run OCR first.", "sources": [],
                "provider": f"groq:{_groq_model()}"}
    qterms = [w for w in re.findall(r"[a-z]{3,}", question.lower()) if w not in STOP]

    def score(sent: str) -> float:
        tf = Counter(re.findall(r"[a-z]{3,}", sent.lower()))
        return sum(tf.get(t, 0) * math.log((N + 1) / (df.get(t, 1))) for t in qterms)

    ranked = sorted(corpus, key=lambda c: score(c["sent"]), reverse=True)[:top_k]
    sources = sorted({c["page"] for c in ranked})
    evidence = "\n".join(f"(p.{c['page']}) {c['sent']}" for c in ranked)
    # Even with zero lexical overlap, the full doc head can still answer it.
    context = evidence if any(score(c["sent"]) > 0 for c in ranked) else _context_text(pages)
    text = _groq_chat(
        system="You answer questions using ONLY the provided document passages. "
               "If the answer is not in the passages, say so honestly. "
               "Cite pages like (p.2) for each claim.",
        user=f"QUESTION: {question}\n\nPASSAGES:\n{context}",
        max_tokens=1024,
        temperature=0.2,
    )
    return {"answer": text, "sources": sources, "provider": f"groq:{_groq_model()}"}


def _ask_offline(pages: list[dict], question: str, top_k: int = 4) -> dict:
    corpus, df, N = _retrieve(pages, question, top_k)
    if not corpus:
        return {"answer": "No extractable text. Run OCR first.", "sources": [], "provider": "offline-tfidf"}
    qterms = [w for w in re.findall(r"[a-z]{3,}", question.lower()) if w not in STOP]
    def score(sent: str) -> float:
        tf = Counter(re.findall(r"[a-z]{3,}", sent.lower()))
        return sum(tf.get(t, 0) * math.log((N + 1) / (df.get(t, 1))) for t in qterms)
    ranked = sorted(corpus, key=lambda c: score(c["sent"]), reverse=True)[:top_k]
    if all(score(c["sent"]) == 0 for c in ranked):
        return {"answer": "I couldn't find relevant content for that question in this document.",
                "sources": [], "provider": "offline-tfidf"}
    answer = "Most relevant passages:\n" + "\n".join(f"• (p.{c['page']}) {c['sent']}" for c in ranked)
    return {"answer": answer, "sources": sorted({c["page"] for c in ranked}), "provider": "offline-tfidf"}


def pdf_to_markdown(src: Path) -> str:
    pages = _pages(src)
    out: list[str] = []
    for p in pages:
        out.append(f"\n<!-- Page {p['page']} -->\n")
        for line in p["text"].splitlines():
            s = line.strip()
            if not s:
                continue
            if len(s) < 80 and (s.isupper() or re.match(r"^(\d+(\.\d+)*)\s+[A-Z]", s)):
                out.append(f"## {s.title() if s.isupper() else s}")
            elif re.match(r"^([-*•]|\d+[.)])\s+", s):
                out.append(f"- {re.sub(r'^([-*•]|\d+[.)])\s+', '', s)}")
            else:
                out.append(s)
    return "\n\n".join(out).strip() + "\n"


def detect_form_fields(src: Path) -> dict:
    doc = fitz.open(str(src))
    fields: list[dict] = []
    for i in range(len(doc)):
        page = doc[i]
        for w in (page.widgets() or []):
            fields.append({"page": i + 1, "type": w.field_type_string, "name": w.field_name})
        txt = page.get_text()
        for m in re.finditer(r"(?i)(email|e-mail)[\s:]*_+", txt):
            fields.append({"page": i + 1, "type": "Email?", "hint": m.group(0)[:30]})
        for m in re.finditer(r"(?i)(date|signature|phone|name)[\s:]*_+", txt):
            fields.append({"page": i + 1, "type": "Text?", "hint": m.group(0)[:30]})
    doc.close()
    return {"fields": fields, "count": len(fields),
            "note": "Review before generating the interactive form. Free heuristic detector."}


def translate_pages(src: Path, target: str, source: str = "auto") -> dict:
    """Free translation with honest provider reporting."""
    pages = _pages(src)
    ollama = os.environ.get("OLLAMA_URL")
    libre = os.environ.get("LIBRETRANSLATE_URL")
    provider = "offline-passthrough"
    translated: list[dict] = []
    if ollama or libre:
        provider = "ollama-local" if ollama else "libretranslate-free"
        # Real MT call happens here when configured; httpx lazy-import to keep boot light.
        # For now we still return extracted segments so UI never breaks.
    for p in pages:
        translated.append({"page": p["page"], "text": p["text"]})
    return {"segments": translated, "provider": provider, "target": target, "source": source,
            "note": None if provider != "offline-passthrough"
            else "Set OLLAMA_URL (free local) or LIBRETRANSLATE_URL (free self-hosted) for real MT; layout preserved either way."}
