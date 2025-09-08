from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import random


app = FastAPI()
templates = Jinja2Templates(directory="templates")

class Card(BaseModel):
    id: int
    question: str
    answer: str


cards = [Card(id = 1, question="Where is Taylor located?", answer="Upland"),
         Card(id=2, question="What is the largest planet in our solar system?", answer="Jupiter"),
         Card(id=3, question="Who wrote the play 'Romeo and Juliet'?", answer="William Shakespeare"),
         Card(id=4, question="What is the capital city of Japan?", answer="Tokyo"),
         Card(id=5, question="When did Ghana gain independence?", answer="6th March, 1957"),
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







