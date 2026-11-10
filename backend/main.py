from __future__ import annotations

import base64
import io
import math
import os
import re
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", CHAT_MODEL)
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=API_KEY) if API_KEY else None
_ocr_engine = None

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xltx", ".xltm"}
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"} | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS | EXCEL_EXTENSIONS

app = FastAPI(title="Multimodal Research Assistant", version="0.1.0")
app.mount("/assets", StaticFiles(directory=FRONTEND), name="assets")

# An intentionally ephemeral index keeps this starter simple and private by default.
documents: dict[str, dict[str, Any]] = {}
passages: list[dict[str, Any]] = []


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    document_ids: list[str] | None = None


def require_ai(feature: str) -> OpenAI:
    if client is None:
        raise HTTPException(
            status_code=400,
            detail=f"Add OPENAI_API_KEY to .env to use {feature}. Text and Excel files work without it.",
        )
    return client


def data_url(content: bytes, suffix: str) -> str:
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}.get(suffix.lower(), "image/jpeg")
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def local_image_details(content: bytes) -> tuple[int, int, str]:
    """Read image dimensions and visible labels without a hosted vision model."""
    try:
        import cv2
        import numpy as np

        image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=422, detail="The image file could not be decoded.")
        height, width = image.shape[:2]
        text = ""
        try:
            global _ocr_engine
            if _ocr_engine is None:
                from rapidocr import RapidOCR

                _ocr_engine = RapidOCR()
            result = _ocr_engine(image)
            text = " ".join(getattr(result, "txts", ()) or ()).strip()
        except Exception:
            # Image indexing should remain available when local OCR models fail to initialize.
            text = ""
        return width, height, text
    except HTTPException:
        raise
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Install OpenCV to read image files.") from exc


def describe_image(content: bytes, suffix: str, instruction: str) -> str:
    width, height, visible_text = local_image_details(content)
    if client is None:
        if visible_text:
            return (
                f"Image ({width} × {height} px). Visible text detected by local OCR: {visible_text}. "
                "Local mode can index labels, but needs OPENAI_API_KEY to interpret the full visual layout."
            )
        return (
            f"Image ({width} × {height} px) uploaded. Add OPENAI_API_KEY to enable visual interpretation; "
            "no readable text was detected locally."
        )
    try:
        result = client.responses.create(
            model=VISION_MODEL,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": instruction},
                    {"type": "input_image", "image_url": data_url(content, suffix), "detail": "high"},
                ],
            }],
        )
        return (result.output_text or "No visual description was returned.").strip()
    except Exception:
        if visible_text:
            return f"Visual interpretation is unavailable. Local OCR detected: {visible_text}"
        return f"Image ({width} × {height} px) uploaded, but visual interpretation is unavailable. Check OPENAI_API_KEY."


def split_passages(text: str, size: int = 1100, overlap: int = 160) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(start + size, len(cleaned))
        if end < len(cleaned):
            boundary = cleaned.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        chunks.append(cleaned[start:end].strip())
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


def extract_pdf(content: bytes, filename: str) -> list[dict[str, Any]]:
    try:
        import fitz
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Install PyMuPDF to read PDF files.") from exc

    results: list[dict[str, Any]] = []
    pdf = fitz.open(stream=content, filetype="pdf")
    for page_index, page in enumerate(pdf):
        page_number = page_index + 1
        page_text = page.get_text("text").strip()
        if page_text:
            results.append({"text": page_text, "locator": f"Page {page_number}", "kind": "text"})

        # Render only pages with embedded figures, retaining vector diagrams as well.
        has_visuals = bool(page.get_images(full=True)) or (not page_text and page_index < 20)
        if not has_visuals:
            try:
                has_visuals = len(page.get_drawings()) >= 20
            except Exception:
                has_visuals = False
        if has_visuals:
            png = page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False).tobytes("png")
            visual = describe_image(
                png,
                ".png",
                "Describe the important visual content on this research-paper page. Read labels in diagrams, explain the flow and relationships, and distinguish visible evidence from inference. Keep it concise.",
            )
            results.append({"text": f"Visual content on page {page_number}: {visual}", "locator": f"Page {page_number} · visual", "kind": "image"})
    if not results:
        raise HTTPException(status_code=422, detail=f"No readable content found in {filename}.")
    return results


def extract_excel(content: bytes) -> list[dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Install openpyxl to read Excel workbooks.") from exc

    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    results: list[dict[str, Any]] = []
    for sheet in workbook.worksheets:
        lines = []
        first_row = None
        last_row = None
        for row_index, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            values = [str(value).strip() if value is not None else "" for value in row]
            if not any(values):
                continue
            first_row = first_row or row_index
            last_row = row_index
            lines.append(f"Row {row_index}: " + " | ".join(value for value in values if value))
        for start in range(0, len(lines), 24):
            group = lines[start:start + 24]
            if group:
                start_row = int(group[0].split(":", 1)[0].split()[-1])
                end_row = int(group[-1].split(":", 1)[0].split()[-1])
                results.append({"text": f"Worksheet {sheet.title}\n" + "\n".join(group), "locator": f"{sheet.title} · rows {start_row}–{end_row}", "kind": "spreadsheet"})
    if not results:
        raise HTTPException(status_code=422, detail="This workbook contains no non-empty cells.")
    return results


def extract_audio(content: bytes, filename: str) -> list[dict[str, Any]]:
    ai = require_ai("audio transcription")
    try:
        transcript = ai.audio.transcriptions.create(model="whisper-1", file=(filename, content))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not transcribe {filename}: {exc}") from exc
    text = getattr(transcript, "text", "").strip()
    if not text:
        raise HTTPException(status_code=422, detail=f"No speech was detected in {filename}.")
    return [{"text": f"Transcript: {text}", "locator": "Transcript", "kind": "audio"}]


def extract_video(content: bytes, filename: str) -> list[dict[str, Any]]:
    require_ai("video understanding")
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Install opencv-python-headless to read video files.") from exc

    suffix = Path(filename).suffix.lower() or ".mp4"
    temp_path = ROOT / f".video-{uuid.uuid4().hex}{suffix}"
    temp_path.write_bytes(content)
    capture = cv2.VideoCapture(str(temp_path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS) or 1.0
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = frame_count / fps if frame_count else 0
        sample_times = sorted(set([0.0, duration / 3, 2 * duration / 3, max(duration - 0.5, 0)]))[:8]
        results = []
        for seconds in sample_times:
            capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
            ok, frame = capture.read()
            if not ok:
                continue
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
            if not ok:
                continue
            visual = describe_image(
                encoded.tobytes(),
                ".jpg",
                "Describe the visible scene and any readable on-screen text. Focus on details useful for answering questions about this video. Do not guess unseen events.",
            )
            results.append({"text": f"Video frame at {seconds:.1f}s: {visual}", "locator": f"Frame · {seconds:.1f}s", "kind": "video"})
        if not results:
            raise HTTPException(status_code=422, detail=f"No readable frames found in {filename}.")
        return results
    finally:
        capture.release()
        temp_path.unlink(missing_ok=True)


def extract_file(content: bytes, filename: str, suffix: str) -> list[dict[str, Any]]:
    if suffix == ".pdf":
        return extract_pdf(content, filename)
    if suffix in EXCEL_EXTENSIONS:
        return extract_excel(content)
    if suffix in IMAGE_EXTENSIONS:
        visual = describe_image(
            content,
            suffix,
            "Describe this image for a research assistant. Include the main objects, layout, any diagram structure or relationships, and readable labels. Separate visible facts from interpretation.",
        )
        return [{"text": f"Image description: {visual}", "locator": "Image", "kind": "image"}]
    if suffix in AUDIO_EXTENSIONS:
        return extract_audio(content, filename)
    if suffix in VIDEO_EXTENSIONS:
        return extract_video(content, filename)
    if suffix in {".txt", ".md"}:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"{filename} is not UTF-8 text.") from exc
        return [{"text": text, "locator": "Text", "kind": "text"}]
    raise HTTPException(status_code=415, detail=f"Unsupported file type: {suffix or 'unknown'}.")


def make_embeddings(texts: list[str]) -> list[list[float]] | None:
    if client is None or not texts:
        return None
    try:
        result = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in result.data]
    except Exception:
        return None


def lexical_score(query: str, text: str) -> float:
    tokens = re.findall(r"[a-z0-9]{2,}", query.lower())
    if not tokens:
        return 0.0
    words = re.findall(r"[a-z0-9]{2,}", text.lower())
    counts = Counter(words)
    unique = set(tokens)
    matched = sum(1 for token in unique if counts[token])
    return matched / max(len(unique), 1) + sum(min(counts[token], 3) for token in unique) / max(len(words), 1)


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    return dot / (norm_left * norm_right) if norm_left and norm_right else 0.0


def add_document(filename: str, source_parts: list[dict[str, Any]], size: int) -> dict[str, Any]:
    document_id = uuid.uuid4().hex
    chunks = []
    for part in source_parts:
        pieces = split_passages(part["text"])
        for piece_index, piece in enumerate(pieces):
            chunks.append({
                "id": uuid.uuid4().hex,
                "document_id": document_id,
                "filename": filename,
                "locator": part["locator"] if len(pieces) == 1 else f"{part['locator']} · excerpt {piece_index + 1}",
                "kind": part["kind"],
                "text": piece,
                "embedding": None,
            })
    embeddings = make_embeddings([chunk["text"] for chunk in chunks])
    if embeddings:
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
    documents[document_id] = {"id": document_id, "name": filename, "size": size, "chunks": len(chunks), "types": sorted({part["kind"] for part in source_parts})}
    passages.extend(chunks)
    return documents[document_id]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "ai_configured": client is not None, "document_count": len(documents), "retrieval": "embeddings" if client else "keyword"}


@app.get("/api/documents")
def list_documents() -> dict[str, Any]:
    return {"documents": list(documents.values())}


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if len(files) > 12:
        raise HTTPException(status_code=413, detail="Upload up to 12 files at a time.")
    added = []
    for uploaded in files:
        filename = Path(uploaded.filename or "upload").name
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(status_code=415, detail=f"{filename}: unsupported file type.")
        content = await uploaded.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"{filename} exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB file limit.")
        if not content:
            raise HTTPException(status_code=422, detail=f"{filename} is empty.")
        parts = extract_file(content, filename, suffix)
        added.append(add_document(filename, parts, len(content)))
    return {"documents": added}


@app.delete("/api/documents/{document_id}")
def remove_document(document_id: str) -> dict[str, bool]:
    if document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found.")
    documents.pop(document_id)
    passages[:] = [passage for passage in passages if passage["document_id"] != document_id]
    return {"ok": True}


@app.post("/api/ask")
def ask(request: AskRequest) -> dict[str, Any]:
    if not documents:
        raise HTTPException(status_code=400, detail="Upload at least one source before asking a question.")
    allowed = set(request.document_ids or documents.keys())
    candidates = [passage for passage in passages if passage["document_id"] in allowed]
    if not candidates:
        raise HTTPException(status_code=400, detail="No indexed passages match the selected sources.")

    query_embedding = make_embeddings([request.question])
    ranked = []
    for passage in candidates:
        if query_embedding and passage["embedding"]:
            score = cosine(query_embedding[0], passage["embedding"])
        else:
            score = lexical_score(request.question, passage["text"])
        ranked.append((score, passage))
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = [item for item in ranked[:8] if item[0] > 0]
    if not selected:
        selected = ranked[:min(4, len(ranked))]

    context = "\n\n".join(
        f"[{passage['filename']} — {passage['locator']}]\n{passage['text']}"
        for _, passage in selected
    )
    if client:
        response = client.responses.create(
            model=CHAT_MODEL,
            instructions=(
                "You are a careful research assistant. Answer using only the supplied source excerpts. "
                "Compare sources directly when asked. If evidence is missing or sources disagree, say so. "
                "Cite claims inline with the exact source label in square brackets, such as [paper.pdf — Page 4]."
            ),
            input=f"Question: {request.question}\n\nSource excerpts:\n{context}",
        )
        answer = (response.output_text or "I couldn't produce an answer from these excerpts.").strip()
        mode = "AI answer · source grounded"
    else:
        local_picks = []
        seen_documents = set()
        for _, passage in selected:
            if passage["document_id"] not in seen_documents:
                local_picks.append(passage)
                seen_documents.add(passage["document_id"])
        for _, passage in selected:
            if passage not in local_picks and len(local_picks) < 3:
                local_picks.append(passage)
        excerpts = "\n\n".join(
            f"\"{passage['text'][:320]}{'…' if len(passage['text']) > 320 else ''}\""
            for passage in local_picks[:3]
        )
        answer = "Top matching excerpts (see the source chips below for locations). Add OPENAI_API_KEY for a synthesized answer.\n\n" + excerpts
        mode = "Relevant excerpts · local keyword search"

    source_rows = []
    seen = set()
    for score, passage in selected[:6]:
        key = (passage["document_id"], passage["locator"])
        if key in seen:
            continue
        seen.add(key)
        source_rows.append({
            "document_id": passage["document_id"],
            "filename": passage["filename"],
            "locator": passage["locator"],
            "kind": passage["kind"],
            "snippet": passage["text"][:260] + ("…" if len(passage["text"]) > 260 else ""),
            "score": round(float(score), 3),
        })
    return {"answer": answer, "sources": source_rows, "mode": mode}
