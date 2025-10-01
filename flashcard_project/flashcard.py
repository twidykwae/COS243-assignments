from urllib import request
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from .db.session import create_db_and_tables, get_session, SessionDep
from sqlmodel import Field, SQLModel, Relationship, select, Session
from fastapi import Depends, Form
import random
from .db.models import Card, Set, User
from .routers import cards, sets
from .core.templates import templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating database and tables...")
    create_db_and_tables()   
    print("Database ready ")
    yield
    print("Shutting down app...")


app = FastAPI(lifespan=lifespan)
app.include_router(cards.router)
app.include_router(sets.router)

templates = Jinja2Templates(directory="templates")

app.mount("/static/css", StaticFiles(directory="static"), name="static")


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


@app.get("/users", response_class=HTMLResponse)
async def get_users(request: Request):
    return templates.TemplateResponse(
        request = request,
        name="users.html", 
        context={"users": user_list}
    )

@app.get("/playwithfriends", response_class=HTMLResponse)
async def playwithfriendspage(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="playwithfriends.html",
    )

@app.post("/playwithfriends", response_class=HTMLResponse)
async def playwithfriends_post(
    request: Request,
    session: Session = Depends(get_session),
    user_name: str = Form(...)
):
    return templates.TemplateResponse(
        request=request,
        name="playwithfriends.html",
        context={"users": user_list, "user_name": user_name}
    )

    