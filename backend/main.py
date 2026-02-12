from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pathlib import Path
import uuid

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


# --- UI landing page (so Replit Preview shows a webpage, not just JSON) ---
@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
      <head>
        <title>Unification v2.0</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
          body { font-family: Arial, sans-serif; background:#0b1220; color:#e6eefc; padding:24px; }
          .card { max-width:720px; margin:0 auto; background:#111a2e; border-radius:18px; padding:24px; box-shadow:0 10px 30px rgba(0,0,0,.35); }
          h1 { margin:0 0 10px; color:#69b7ff; }
          .ok { color:#4ade80; font-weight:700; }
          code { background:#0b1220; padding:4px 8px; border-radius:8px; }
          a { color:#9dd6ff; }
          .row { margin:10px 0; line-height:1.45; }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Unification v2.0</h1>
          <div class="row"><span class="ok">Status:</span> Running</div>
          <div class="row">Mode: Basketball 1H Structural Analysis</div>
          <div class="row">OCR Available: <b>%s</b></div>
          <div class="row">Health: <code>/health</code></div>
          <div class="row">Docs: <a href="/docs">/docs</a></div>
          <div class="row">Upload: <code>POST /upload</code> (image file)</div>
        </div>
      </body>
    </html>
    """ % ("YES" if OCR_AVAILABLE else "NO")


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
        return {"ok": True, "file_id": file_id, "text": raw[:8000]}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "OCR failed", "detail": str(e)}
        )


def parse_ladder_from_text(raw_text: str):
    """
    Parser stub.
    Next step will extract structured ladder rows.
    """
    text = raw_text.replace("\n", " ").strip()
    lowered = text.lower()

    signals = {
        "mentions_over": "over" in lowered,
        "mentions_under": "under" in lowered,
        "mentions_total": "total" in lowered or "totals" in lowered,
        "mentions_1st_half": "1st" in lowered or "1 half" in lowered or "first half" in lowered
    }

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

        return {"ok": True, "file_id": file_id, "parsed": parsed}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "Parse failed", "detail": str(e)}
        )