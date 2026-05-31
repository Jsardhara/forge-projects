import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from app import app, Prompt, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)

def test_create_and_list_prompt():
    # create
    resp = client.post("/prompts", json={"title": "Hello", "content": "World"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Hello"
    # list
    resp = client.get("/prompts")
    assert resp.status_code == 200
    lst = resp.json()
    assert len(lst) == 1
    assert lst[0]["title"] == "Hello"
