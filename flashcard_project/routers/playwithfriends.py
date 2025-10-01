from fastapi import APIRouter

router = APIRouter(prefix="/play-with-friends")

@router.get('/')
def play_with_friends():
    return {"message": "Play with friends"}

