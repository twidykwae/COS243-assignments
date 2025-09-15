from urllib import request
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from db.session import create_db_and_tables, get_session, SessionDep
from sqlmodel import Field, SQLModel, Relationship, select
import random


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

class Card(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    front: str
    back: str
    set_ID: int = Field(foreign_key="set.id")
    set: "Set" = Relationship(back_populates="cards")

class User(BaseModel):
    id: int
    name: str
    email: str
    sets: list[int] = []

class Set(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    cards: list["Card"] = Relationship(back_populates="set")



user_list = [User(id=1, name="Twidy", email="twidy@gmail.com", sets=[1]),
             User(id=2, name="Jake", email="jake@gmail.com", sets=[2]),
             ]


set_list = [Set(id=1, name="Geography"),
            Set(id=2, name="History")
            ]

cards = [Card(id = 1, question="Where is Taylor located?", answer="Upland", set_ID=1),
         Card(id=2, question="What is the largest planet in our solar system?", answer="Jupiter", set_ID=1),
         Card(id=3, question="Who wrote the play 'Romeo and Juliet'?", answer="William Shakespeare", set_ID=2),
         Card(id=4, question="What is the capital city of Japan?", answer="Tokyo", set_ID=2),
         Card(id=5, question="When did Ghana gain independence?", answer="6th March, 1957", set_ID=2),
         ]



@app.get("/", response_class=HTMLResponse)
async def read_root(request:Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"cards": cards}
    )


@app.get("/play", response_class=HTMLResponse)
async def play(request: Request):
    card = cards[random.randint(0, (len(cards)-1))]
    return templates.TemplateResponse(
        request = request, name="play.html", context={"card": card}
    )



@app.get("/cards/{card_id}", name="get_card", response_class=HTMLResponse)
async def get_card_by_id(card_id: int, request: Request):
    for card in cards:
        if card.id == card_id:
            return templates.TemplateResponse(
                request = request,
                name="card.html", context={"card": card}
            )

@app.get("/sets", response_class=HTMLResponse)
async def get_set(request: Request):
    return templates.TemplateResponse(
        request = request,
        name="sets.html", 
        context={"sets": set_list}
    )

@app.get("/users", response_class=HTMLResponse)
async def get_users(request: Request):
    return templates.TemplateResponse(
        request = request,
        name="users.html", 
        context={"users": user_list}
    )