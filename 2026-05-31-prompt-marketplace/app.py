from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import List
import os

app = FastAPI(title="Prompt Marketplace")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./prompts.db")
engine = create_engine(DATABASE_URL, echo=False)

class Prompt(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    title: str
    content: str
    author: str = "anonymous"

def get_session():
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

@app.get("/prompts", response_model=List[Prompt])
def list_prompts(session: Session = Depends(get_session)):
    prompts = session.exec(select(Prompt)).all()
    return prompts

@app.post("/prompts", response_model=Prompt)
def create_prompt(prompt: Prompt, session: Session = Depends(get_session)):
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return prompt
