from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Unification v2.0 Engine")

# Allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "engine": "Unification v2.0",
        "status": "running",
        "mode": "Basketball 1H Structural Analysis"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
