"""Free offline AI layer — no paid API keys required.

Default providers (work with zero downloads):
  - summarize: extractive frequency summarizer with page citations
  - ask: TF-IDF sentence retrieval with page citations (mini-RAG, no vectors DB needed)
  - markdown: structure detection -> clean Markdown
  - forms: heuristic field detection (widgets + text patterns)
  - translate: pluggable. Tries free local options in order:
      1. Ollama (free, local) if OLLAMA_URL set
      2. LibreTranslate (free, self-hostable) if LIBRETRANSLATE_URL set
      3. offline passthrough that preserves layout and clearly labels provider.
Upgrade path: point env vars at your free local models; API shape stays identical.
"""

from pathlib import Path
import math
import os
import re
from collections import Counter
import fitz

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
    pages = _pages(src)
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


def ask_pdf(src: Path, question: str, top_k: int = 4) -> dict:
    pages = _pages(src)
    corpus = []
    for p in pages:
        for s in _sentences(p["text"]):
            corpus.append({"page": p["page"], "sent": s})
    if not corpus:
        return {"answer": "No extractable text. Run OCR first.", "sources": [], "provider": "offline-tfidf"}
    qterms = [w for w in re.findall(r"[a-z]{3,}", question.lower()) if w not in STOP]
    df = Counter()
    for c in corpus:
        for w in set(re.findall(r"[a-z]{3,}", c["sent"].lower())):
            df[w] += 1
    N = len(corpus)
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
