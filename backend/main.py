from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import uuid
import os

# Optional OCR stack
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

app = FastAPI(title="Unification v2.0 Engine")

# Allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def root():
    return {
        "engine": "Unification v2.0",
        "status": "running",
        "mode": "Basketball 1H Structural Analysis",
        "ocr_available": OCR_AVAILABLE
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/upload")
async def upload_screenshot(file: UploadFile = File(...)):
    """
    Upload a screenshot (SportyBet or 1xBet).
    Returns file_id + saved path.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported.")

    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix.lower() if file.filename else ".png"
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        ext = ".png"

    save_path = UPLOAD_DIR / f"{file_id}{ext}"

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")

    save_path.write_bytes(content)

    return {
        "ok": True,
        "file_id": file_id,
        "filename": save_path.name,
        "stored_at": str(save_path),
        "next": {
            "extract_text": f"/extract/{file_id}",
            "parse": f"/parse/{file_id}"
        }
    }


def _find_file_by_id(file_id: str) -> Path:
    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="File not found. Upload first.")
    return matches[0]


@app.get("/extract/{file_id}")
def extract_text(file_id: str):
    """
    OCR the uploaded screenshot to raw text.
    """
    img_path = _find_file_by_id(file_id)

    if not OCR_AVAILABLE:
        return JSONResponse(
            status_code=501,
            content={
                "ok": False,
                "error": "OCR dependencies not available in this environment.",
                "hint": "We will switch to an alternative extractor if needed."
            }
        )

    try:
        img = Image.open(img_path)
        raw = pytesseract.image_to_string(img)
        raw = raw.strip()
        return {"ok": True, "file_id": file_id, "text": raw[:8000]}  # cap for safety
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "OCR failed", "detail": str(e)}
        )


def parse_ladder_from_text(raw_text: str):
    """
    Very first stub parser.
    For now: returns detected tokens and placeholders.

    Next iteration will:
    - detect Over/Under columns
    - detect total lines (e.g. 84.5, 85.5)
    - map odds to each line
    """
    text = raw_text.replace("\n", " ").strip()
    lowered = text.lower()

    signals = {
        "mentions_over": "over" in lowered,
        "mentions_under": "under" in lowered,
        "mentions_total": "total" in lowered or "totals" in lowered,
        "mentions_1st_half": "1st" in lowered or "1 half" in lowered or "first half" in lowered
    }

    # Placeholder: actual ladder extraction comes next
    return {
        "signals": signals,
        "raw_sample": text[:500],
        "ladder": None,
        "note": "Parser v1 stub. Next step will extract structured ladder rows."
    }


@app.get("/parse/{file_id}")
def parse_uploaded(file_id: str):
    """
    OCR + parse into structured ladder JSON.
    """
    img_path = _find_file_by_id(file_id)

    if not OCR_AVAILABLE:
        return JSONResponse(
            status_code=501,
            content={"ok": False, "error": "OCR not available; cannot parse yet."}
        )

    try:
        img = Image.open(img_path)
        raw = pytesseract.image_to_string(img).strip()
        parsed = parse_ladder_from_text(raw)

        return {
            "ok": True,
            "file_id": file_id,
            "parsed": parsed
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "Parse failed", "detail": str(e)}
        )
