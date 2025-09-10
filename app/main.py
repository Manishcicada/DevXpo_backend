from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, Response
from sqlmodel import SQLModel, Session, create_engine, select
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
import uuid
import aiofiles
from dotenv import load_dotenv
from app import models, services

load_dotenv()

DB_URL = "sqlite:///./data.db"
engine = create_engine(DB_URL, echo=False)
app = FastAPI(title="AI Courtroom MVP")

# Directory for uploaded files
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Courtroom MVP API"}


# Favicon handler
@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


# ---- CASE CREATION ----
@app.post("/cases")
def create_case(payload: models.CaseCreate):
    with Session(engine) as sess:
        case = models.Case.model_validate(payload)
        sess.add(case)
        sess.commit()
        sess.refresh(case)
        return case


# ---- EVIDENCE UPLOAD ----
@app.post("/cases/{case_id}/evidence")
async def upload_evidence(
    case_id: int,
    file: UploadFile = File(...),
    party: str = Form(...)
):
    with Session(engine) as sess:
        case = sess.get(models.Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        filename = f"{uuid.uuid4().hex}_{file.filename}"
        dest = UPLOAD_DIR / filename

        async with aiofiles.open(dest, "wb") as out:
            content = await file.read()
            await out.write(content)

        text = services.extract_text_from_file(dest)

        ev = models.Evidence(
            case_id=case_id,
            filename=file.filename,
            stored_path=str(dest),
            extracted_text=text,
            party=party,
        )
        sess.add(ev)
        sess.commit()
        sess.refresh(ev)
        return ev


# ---- CASE SIMULATION ----
@app.post("/cases/{case_id}/simulate")
def simulate(case_id: int):
    with Session(engine) as sess:
        case = sess.get(models.Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Fetch evidence by party
        defense_evidence = sess.exec(
            select(models.Evidence).where(
                (models.Evidence.case_id == case_id)
                & (models.Evidence.party == "Defense")
            )
        ).all()

        opposition_evidence = sess.exec(
            select(models.Evidence).where(
                (models.Evidence.case_id == case_id)
                & (models.Evidence.party == "Opposition")
            )
        ).all()

        # Build payload dict expected by services.run_simulation
        payload = {
            "caseInfo": {
                "title": case.title,
                "caseType": case.case_type,
                "incidentDate": "Unknown",
                "location": "Unknown",
            },
            "userClaim": {
                "mainClaim": case.description,
                "objective": "Win case",
                "supportingStatement": "The defense has evidence to support its position.",
            },
            "evidence": {
                "files": [ev.stored_path for ev in (defense_evidence + opposition_evidence)]
            },
            "opposition": {
                "anticipatedArguments": "The opposition disagrees with the claim.",
                "probableWeaknesses": "Insufficient proof.",
            },
            "simulationSettings": {
                "trialDepth": "standard",   # later can be configurable
                "tone": "formal",
                "verdictOutput": "summary",
            },
        }

        transcript, judge = services.run_simulation(payload)

        # Save transcript lines
        for t in transcript:
            entry = models.Transcript(
                case_id=case_id,
                agent=t["agent"],
                content=t["content"]
            )
            sess.add(entry)

        # Save judge result
        judge_row = models.JudgeResult(
            case_id=case_id,
            win_probability=judge["win_probability"],
            breakdown=str(judge.get("breakdown", "")),
            justification=judge.get("justification", ""),
        )
        sess.add(judge_row)

        sess.commit()

        return {"transcript": transcript, "judge": judge}


# ---- CASE TRANSCRIPT ----
@app.get("/cases/{case_id}/transcript")
def get_transcript(case_id: int):
    with Session(engine) as sess:
        case = sess.get(models.Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        trans = sess.exec(
            select(models.Transcript).where(models.Transcript.case_id == case_id)
        ).all()

        judge = sess.exec(
            select(models.JudgeResult).where(models.JudgeResult.case_id == case_id)
        ).first()

        return {"case": case, "transcript": trans, "judge": judge}
