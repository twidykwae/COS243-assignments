from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse 
from sqlmodel import Session, select
from ..db.session import get_session   
from ..db.models import Card
from ..core.templates import templates
from ..db.models import Set

router = APIRouter(prefix="/cards")

@router.get("/", response_class=HTMLResponse)
async def get_cards(request: Request, session: Session = Depends(get_session)):
    cards = session.exec(select(Card)).all()
    return templates.TemplateResponse(
        request=request, name="/cards/cards.html", context={"cards": cards}
    )

@router.get("/add", response_class=HTMLResponse)
async def add_card_form(request: Request, session: Session = Depends(get_session)):
    sets = session.exec(select(Set)).all()
    return templates.TemplateResponse(
        "cards/add_card.html",
        {"request": request, "sets": sets}
    )

@router.post("/add", response_class=RedirectResponse)
async def add_card(request: Request, session: Session = Depends(get_session), 
                   front: str = Form(...), back: str = Form(...), set_ID: int = Form(...)):
    new_card = Card(
        front=front,
        back=back,
        set_ID=set_ID,
    )
    session.add(new_card)
    session.commit()
    session.refresh(new_card)
    return RedirectResponse(url="/cards", status_code=302)


@router.get("/{card_id}", response_class=HTMLResponse)
async def get_card(request: Request, card_id: int, session: Session = Depends(get_session)):
    card = session.exec(select(Card).where(Card.id == card_id)).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return templates.TemplateResponse(
        request=request, name="cards/card_details.html", context={"request": request, "card": card}
    )


@router.get("/{card_id}/edit", response_class=HTMLResponse)
async def edit_card(request: Request, session: Session = Depends(get_session), card_id: int = None):
    card = session.exec(select(Card).where(Card.id == card_id)).first()
    sets = session.exec(select(Set)).all()
    if not card:
        raise HTTPException(404, "Card not found")
    return templates.TemplateResponse(
        request=request,
        name="cards/add_card.html",
        context={"card": card, "sets": sets}
    )

@router.post("/{card_id}/edit")
async def update_card(
    card_id: int,
    session: Session = Depends(get_session),
    front: str = Form(...),
    back: str = Form(...),
    set_ID: int = Form(...)
):
    card = session.exec(select(Card).where(Card.id == card_id)).first()
    if not card:
        raise HTTPException(404, "Card not found")
    card.front, card.back, card.set_ID = front, back, set_ID
    session.add(card)
    session.commit()
    return RedirectResponse(url=f"/cards/{card.id}", status_code=302)


@router.post("/{card_id}/delete")
async def delete_card(card_id: int, session: Session = Depends(get_session)):
    card = session.exec(select(Card).where(Card.id == card_id)).first()
    if not card:
        raise HTTPException(404, "Card not found")
    session.delete(card)
    session.commit()
    return RedirectResponse(url="/cards", status_code=302)
