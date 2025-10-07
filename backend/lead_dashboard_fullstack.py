# fastapi_lead_backend.py
# FastAPI backend to connect Lead Quality Scorer & Prioritizer with the React UI

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from backend.lead_quality_prioritizer import score_leads  # scoring functions

app = FastAPI()

# Allow CORS from React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] ,  # in production, replace with frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/score')
async def upload_file(file: UploadFile = File(...)):
    # Read CSV content
    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid or empty CSV: {str(e)}")

    # Score leads; score_leads returns a list of dicts
    scored_leads = score_leads(df)
    return scored_leads

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)
