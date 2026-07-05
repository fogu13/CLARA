"""Standalone FastAPI wrapper for the compliance checker.

Run:  cd add-ons/compliance-checker && pip install -r requirements.txt
      AI_BASE_URL=... AI_API_KEY=... AI_MODEL=... uvicorn app:app --reload

To fold into CLARA: lift this router into apps/api (mount under /compliance) and
swap compliance._call_tool for app.services.ai.call_tool.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from compliance import ComplianceError, assess_compliance

app = FastAPI(title="CLARA add-on — EU AI Act + GDPR compliance checker")


class Document(BaseModel):
    name: str
    content: str


class CheckRequest(BaseModel):
    title: str = Field(min_length=1)
    campaign_description: str = Field(min_length=1)
    additional_documents: list[Document] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/compliance/check")
def check(request: CheckRequest) -> dict:
    try:
        return assess_compliance(
            title=request.title,
            campaign_description=request.campaign_description,
            additional_documents=[d.model_dump() for d in request.additional_documents],
        )
    except ComplianceError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
