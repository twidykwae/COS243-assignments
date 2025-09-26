from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
from flashcard import app, get_session
from sqlmodel import Session, Field, SQLModel, create_engine, select, Relationship
import re

def test_read_main():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

def test_create_set():
    #Setup a test database so that we don't create data in our real database.
    #Use this database for testing
    engine = create_engine(  
        "sqlite:///test.db", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)  

    with Session(engine) as session:  
        def get_session_override():
            return session  
        app.dependency_overrides[get_session] = get_session_override  

    client = TestClient(app)
    
    #Post our set data and save the response
    response = client.post(
        "/sets/add", data={"name":"Science"}
    )
    
    #Ensure that the response returns status code '200 ok'
    #Ensure that the page returned html, not json
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text
    #Does the name of our set we created appear in the html?
    assert "Science" in html
    
    #Access newly created set on its page by id
    #Search the page using regex to pull the id out of the link
    match = re.search(r"/sets/(\d+)", html)
    assert match is not None
    #save the set ide
    item_id = match.group(1)
    
    #Call the get sets page with that id
    response = client.get("/sets/"+item_id)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "Science" in html

    #BEAUTIFUL SOUP Test
    soup = BeautifulSoup(html, 'html.parser')
    headers = soup.find_all('h1')
    assert headers[1].text == "Science"
    

    #Newly Created set shows up on the set page
    response = client.get("/sets/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "Science" in html    
    app.dependency_overrides.clear()