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

app.mount("/static/css", StaticFiles(directory="static"), name="static")

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


@app.get("/", response_class=HTMLResponse)
async def read_root(request:Request, session: SessionDep):
    cards = session.exec(select(Card)).all()
    return templates.TemplateResponse(
        request=request, name="index.html", context={"cards": cards}
    )


@app.get("/play", response_class=HTMLResponse)
async def play(request: Request, session: SessionDep):
    cards = session.exec(select(Card)).all()
    random_card = random.choice(cards) if cards else None
    return templates.TemplateResponse(
        request=request, name="play.html", context={"card": random_card}
    )


@app.get("/cards", response_class=HTMLResponse)
async def get_cards(request: Request, session: SessionDep):
    cards = session.exec(select(Card)).all()
    return templates.TemplateResponse(
        request=request, name="cards.html", context={"cards": cards}
    )

@app.get("/cards/{card_id}", name="get_card", response_class=HTMLResponse)
async def get_card_by_id(card_id: int, request: Request, session: SessionDep):
    card = session.exec(select(Card).where(Card.id == card_id)).first()
    if card:
        return templates.TemplateResponse(
            request=request,
            name="card.html", context={"card": card}
            )

@app.get("/sets", response_class=HTMLResponse)
async def get_set(request: Request, session: SessionDep):
    sets = session.exec(select(Set).order_by(Set.name)).all()
    return templates.TemplateResponse(
        request=request, name="sets.html", context={"sets":sets}
    )


@app.get("/sets/{set_id}", name="get_set", response_class=HTMLResponse)
async def get_set_by_id(set_id: int, request: Request, session: SessionDep):
    set = session.exec(select(Set).where(Set.id == set_id)).first()
    if set:
        return templates.TemplateResponse(
            request=request,
            name="set_detail.html",
            context={"set": set, "cards": set.cards}
            )

@app.get("/users", response_class=HTMLResponse)
async def get_users(request: Request):
    return templates.TemplateResponse(
        request = request,
        name="users.html", 
        context={"users": user_list}
    )


@app.post("/sets/add")
async def create_set(session: SessionDep, set:Set):
    db_set = Set(name=set.name)
    session.add(db_set)
    session.commit()
    session.refresh(db_set)
    return db_set


@app.post("/cards/add")
async def create_card(session: SessionDep, card:Card):
    db_card = Card(front=card.front, back=card.back, set_ID=card.set_ID)
    session.add(db_card)
    session.commit()
    session.refresh(db_card)
    return db_card

