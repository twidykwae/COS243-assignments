from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse    
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from ..db.session import SessionDep, get_session   
from ..db.models import Set
from fastapi import Depends, Form, HTTPException
from ..core.templates import templates  
router = APIRouter(prefix="/sets")

@router.get("/", response_class=HTMLResponse)
async def get_set(request: Request, session: SessionDep):
    sets = session.exec(select(Set).order_by(Set.name)).all()
    return templates.TemplateResponse(
        request=request, name="/sets/sets.html", context={"sets":sets}
    )
@router.get("/add")
async def add_set(request: Request):
    return templates.TemplateResponse(
        request=request, name="/sets/add_sets.html", context={}
    )

@router.post("/add")
async def create_set(request: Request, session: Session = Depends(get_session), 
                   name: str = Form(...)):
    new_set = Set(
        name=name,
    )
    session.add(new_set)
    session.commit()
    session.refresh(new_set)
    return RedirectResponse(url="/sets", status_code=302)

@router.get("/{set_id}", name="get_set", response_class=HTMLResponse)
async def get_set_by_id(set_id: int, request: Request, session: SessionDep):
    set = session.exec(select(Set).where(Set.id == set_id)).first()
    if set:
        return templates.TemplateResponse(
            request=request,
            name="/sets/set_detail.html",
            context={"set": set, "cards": set.cards}
            )

