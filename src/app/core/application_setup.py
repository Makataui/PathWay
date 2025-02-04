from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..models import *
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
from .logger import logging


from .config import (
    AppSettings,
    ClientSideCacheSettings,
    DatabaseSettings,
    EnvironmentOption,
    EnvironmentSettings,
    RedisCacheSettings,
    RedisQueueSettings,
    RedisRateLimiterSettings,
    settings,
)

from .db.database import Base, async_engine as engine
from .utils import cache, queue, rate_limit
app = FastAPI()

# Setup Jinja templates
app.mount("/static", StaticFiles(directory="static"), name="static")
# Define templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
# Initialize Jinja2
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Route to display SDC form creator page
@app.get("/all_forms/", response_class=HTMLResponse)
async def sdc_form_page(request: Request, db: Session = Depends(get_db)):
    sdc_forms = db.query(SDCForm).all()
    return templates.TemplateResponse("sdc_form.html", {"request": request, "sdc_forms": sdc_forms})

# Endpoint to create an SDC form
@app.post("/create_sdc_form/")
async def create_sdc_form(name: str = Form(...), db: Session = Depends(get_db)):
    sdc_form = SDCForm(name=name)
    db.add(sdc_form)
    db.commit()
    db.refresh(sdc_form)
    return {"message": "SDC Form created", "id": sdc_form.id}

# Endpoint to add a question to an SDC form
@app.post("/add_sdc_question/")
async def add_sdc_question(
    sdc_form_id: int = Form(...),
    text: str = Form(...),
    type: AnswerTypeEnum = Form(...),
    unit_of_measurement: str = Form(None),
    options: str = Form(None),
    db: Session = Depends(get_db)
):
    sdc_form = db.query(SDCForm).filter(SDCForm.id == sdc_form_id).first()
    if not sdc_form:
        raise HTTPException(status_code=404, detail="SDC Form not found")

    sdc_question = SDCQuestion(
        sdc_form_id=sdc_form_id,
        text=text,
        type=type,
        unit_of_measurement=unit_of_measurement,
        options=options
    )

    db.add(sdc_question)
    db.commit()
    db.refresh(sdc_question)
    return {"message": "SDC Question added", "id": sdc_question.id}

# Endpoint to view an SDC form and its questions
@app.get("/view_sdc_form/{sdc_form_id}", response_class=HTMLResponse)
async def view_sdc_form(request: Request, sdc_form_id: int, db: Session = Depends(get_db)):
    sdc_form = db.query(SDCForm).filter(SDCForm.id == sdc_form_id).first()
    if not sdc_form:
        raise HTTPException(status_code=404, detail="SDC Form not found")

    return templates.TemplateResponse(
        "sdc_view_form.html", {"request": request, "sdc_form": sdc_form}
    )
