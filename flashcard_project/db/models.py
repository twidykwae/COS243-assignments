from sqlmodel import Field, SQLModel, Relationship
from pydantic import BaseModel
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

