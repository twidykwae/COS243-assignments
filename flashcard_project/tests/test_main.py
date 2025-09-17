from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
from flashcard import app, get_session

def test_read_main():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200