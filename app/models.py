from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class Case(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    case_type: Optional[str] = "general"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CaseCreate(BaseModel):
    title: str
    description: str
    case_type: Optional[str] = "general"

class Evidence(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int
    filename: str
    stored_path: str
    extracted_text: Optional[str] = ""
    party: Optional[str] = None

class Transcript(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int
    agent: str
    content: str

class JudgeResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int
    win_probability: float
    breakdown: str
    justification: str
