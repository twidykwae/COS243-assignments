import json
import random
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlmodel import select, Session, SQLModel, Field
from .db.session import create_db_and_tables, get_session, SessionDep
from .db.models import Card, Set, User
from .routers import cards, sets
from .core.templates import templates


# ---------------- Connection Manager ---------------- #
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(username, []).append(websocket)

    def disconnect(self, username: str, websocket: WebSocket):
        if username in self.active_connections:
            if websocket in self.active_connections[username]:
                self.active_connections[username].remove(websocket)
            if not self.active_connections[username]:
                del self.active_connections[username]

    async def broadcast(self, message: dict):
        dead = []
        for user, sockets in list(self.active_connections.items()):
            for ws in sockets[:]:  # Create a copy of the list
                try:
                    await ws.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to {user}: {e}")
                    dead.append((user, ws))
        for user, ws in dead:
            self.disconnect(user, ws)
            
    async def send_personal_message(self, username: str, message: dict):
        if username in self.active_connections:
            dead = []
            for ws in self.active_connections[username][:]:  # Create a copy
                try:
                    await ws.send_json(message)
                except Exception as e:
                    print(f"Error sending to {username}: {e}")
                    dead.append((username, ws))
            for user, ws in dead:
                self.disconnect(user, ws)

    def get_connected_users(self):
        """Get list of currently connected users"""
        return list(self.active_connections.keys())

manager = ConnectionManager()


# ---------------- Game Manager ---------------- #
class GameManager:
    def __init__(self):
        self.ready_players = set()
        self.current_question = None
        self.question_options = []
        self.correct_answer = None
        self.scores = {}
        self.game_active = False
        self.round_number = 0
        self.max_rounds = 10
        self.answered_this_round = set()
        self.game_lock = asyncio.Lock()  # Prevent race conditions

    def mark_ready(self, username):
        """Mark a player as ready"""
        self.ready_players.add(username)
        if username not in self.scores:
            self.scores[username] = 0

    def unmark_ready(self, username):
        """Remove ready status from a player"""
        self.ready_players.discard(username)

    def reset_ready(self):
        """Clear all ready states"""
        self.ready_players.clear()

    def all_ready(self, connected_users):
        """Check if all connected users are ready"""
        if len(connected_users) < 2:  # Need at least 2 players
            return False
        ready_norm = {u.strip().lower() for u in self.ready_players}
        connected_norm = {u.strip().lower() for u in connected_users}
        print(f"Ready check - Ready: {ready_norm}, Connected: {connected_norm}")
        return len(ready_norm) >= 2 and ready_norm == connected_norm

    def choose_random_question(self, session: Session):
        """Select a random question and generate options"""
        cards = session.exec(select(Card)).all()
        if not cards:
            return None

        question = random.choice(cards)
        self.current_question = question
        self.correct_answer = question.back
        self.answered_this_round.clear()

        # Create multiple choice options
        options = [question.back]
        all_backs = [c.back for c in cards if c.back != question.back]
        
        # Get 3 more unique options
        if len(all_backs) >= 3:
            selected = random.sample(all_backs, 3)
            options.extend(selected)
        else:
            # Not enough unique options, use what we have
            options.extend(all_backs)
            while len(options) < 4:
                options.append(f"{question.back} (variant {len(options)})")
            
        random.shuffle(options)
        self.question_options = options
        return question

    def check_answer(self, username, answer):
        """Check if an answer is correct and update scores"""
        if not self.game_active or not self.current_question:
            return None
        if username in self.answered_this_round:
            return None
            
        self.answered_this_round.add(username)
        is_correct = (answer.strip() == self.correct_answer.strip())
        
        if is_correct:
            self.scores[username] = self.scores.get(username, 0) + 1
        
        return is_correct

    def get_sorted_scores(self):
        """Get scores sorted by value (highest first)"""
        return sorted(self.scores.items(), key=lambda x: x[1], reverse=True)

    def reset_game(self):
        """Reset game state for a new game"""
        self.ready_players.clear()
        self.current_question = None
        self.question_options = []
        self.correct_answer = None
        self.scores = {}
        self.game_active = False
        self.round_number = 0
        self.answered_this_round.clear()

    def cleanup_player(self, username):
        """Remove player from active game state"""
        self.ready_players.discard(username)
        self.answered_this_round.discard(username)


game = GameManager()


# ---------------- Lifespan / App Init ---------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating database and tables...")
    create_db_and_tables()
    print("Database ready.")
    yield
    print("Shutting down app...")


app = FastAPI(lifespan=lifespan)
app.include_router(cards.router)
app.include_router(sets.router)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------- Routes ---------------- #
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, session: SessionDep):
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
async def get_users(request: Request, session: SessionDep):
    user_list = session.exec(select(User)).all()
    return templates.TemplateResponse(
        request=request,
        name="users.html",
        context={"users": user_list}
    )


@app.get("/users/create", response_class=HTMLResponse)
async def create_user_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="users_create.html",
        context={}
    )
@app.post("/users/create", response_class=HTMLResponse)
async def create_user(request: Request, session: SessionDep, name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    name = name.strip()
    email = email.strip()
    password = password.strip()
    if not name or not password:
        return templates.TemplateResponse(
            request=request,
            name="users_create.html",
            context={"error": "Name and password cannot be empty"}
        )
    
    existing = session.exec(select(User).where(User.name == name)).first()
    if existing:
        return templates.TemplateResponse(
            request=request,
            name="users_create.html",
            context={"error": "Name already registered"}
        )

    new_user = User(name=name, email=email, password=password)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return RedirectResponse(url="/playwithfriends", status_code=303)

    


@app.get("/playwithfriends", response_class=HTMLResponse)
async def play_game(request: Request):
    return templates.TemplateResponse(
        request=request, name="playwithfriends.html", context={"user_name": None}
    )


@app.post("/playwithfriends", response_class=HTMLResponse)
async def enter_play(request: Request, user_name: str = Form(...), session: Session = Depends(get_session)):
    user_name = user_name.strip()
    if not user_name:
        return templates.TemplateResponse(
            request=request, 
            name="playwithfriends.html", 
            context={"user_name": None, "error": "Username cannot be empty"}
        )

    user = session.exec(select(User).where(user_name == User.name)).first()

    if not user:
        return templates.TemplateResponse(
            request=request, 
            name="users_create.html", 
            context={"user_name": None, "error": "Username not registered"}
        )
    
    response = templates.TemplateResponse(
        request=request, name="playwithfriends.html", context={"user_name": user_name}
    )
    response.set_cookie(key="user_name", value=user_name, httponly=False)
    return response


# ---------------- WebSocket Trivia Logic ---------------- #
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str, session: Session = Depends(get_session)):
    username = username.strip()
    if not username:
        await websocket.close(code=1008, reason="Invalid username")
        return
        
    await manager.connect(username, websocket)
    
    if username not in game.scores:
        game.scores[username] = 0
    
    connected_users = manager.get_connected_users()
    
    # Broadcast updated player list to everyone
    await manager.broadcast({
        "type": "lobby",
        "players": connected_users
    })
    
    # Send current scores
    await manager.broadcast({
        "type": "score_update",
        "scores": game.get_sorted_scores()
    })
    
    # If game is active, send current question to new player
    if game.game_active and game.current_question:
        await manager.send_personal_message(username, {
            "type": "new_question",
            "question": game.current_question.front,
            "options": game.question_options,
            "round": game.round_number,
            "total_rounds": game.max_rounds
        })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "chat_message":
                message = data.get("message", "").strip()
                if message:
                    await manager.broadcast({
                        "type": "chat_message",
                        "sender": username,
                        "message": message
                    })

            elif msg_type == "ready":
                async with game.game_lock:  # Prevent race conditions
                    if game.game_active:
                        await manager.send_personal_message(username, {
                            "type": "info",
                            "message": "Game already in progress!"
                        })
                        continue
                    
                    game.mark_ready(username)
                    connected_users = manager.get_connected_users()
                    
                    await manager.broadcast({
                        "type": "ready_update",
                        "ready_players": list(game.ready_players),
                        "players": connected_users
                    })

                    # Start game when all ready
                    if game.all_ready(connected_users):
                        game.game_active = True
                        game.round_number = 0
                        
                        await manager.broadcast({
                            "type": "game_starting",
                            "message": "Game starting in 3 seconds..."
                        })
                        
                        await asyncio.sleep(3)
                        game.reset_ready()  # Clear ready states after countdown
                        await start_new_round(session)

            elif msg_type == "answer":
                answer = data.get("answer", "").strip()
                if not answer:
                    continue
                

                async with game.game_lock:
                    result = game.check_answer(username, answer)

                if result is None:
                    await manager.send_personal_message(username, {
                        "type": "info",
                        "message": "Answer not counted (already answered or round inactive)"
                    })
                    continue

                if result is True:
                    await manager.broadcast({
                        "type": "answer_result",
                        "username": username,
                        "correct": True,
                        "correct_answer": game.correct_answer,
                        "scores": game.get_sorted_scores(),
                        "message": f"{username} got it right! +1 point"
                    })
                    


                    if game.answered_this_round == set(manager.get_connected_users()):
                        await asyncio.sleep(2)
                        game.round_number += 1
                    
                        if game.round_number >= game.max_rounds:
                            await end_game()
                        else:
                            await start_new_round(session)
                else:
                    await manager.send_personal_message(username, {
                        "type": "answer_result",
                        "username": username,
                        "correct": False,
                        "message": "Incorrect - keep trying!"
                    })

    except WebSocketDisconnect:
        manager.disconnect(username, websocket)
        game.cleanup_player(username)
        
        remaining_users = manager.get_connected_users()
        await manager.broadcast({
            "type": "user_left",
            "username": username,
            "players": remaining_users
        })
        
        # End game if too few players remain
        if game.game_active and len(remaining_users) < 2:
            await manager.broadcast({
                "type": "game_over",
                "message": "Game ended - not enough players",
                "scores": game.get_sorted_scores()
            })
            game.reset_game()
    
    except Exception as e:
        print(f"WebSocket error for {username}: {e}")
        manager.disconnect(username, websocket)
        game.cleanup_player(username)


# ---------------- Helper Functions ---------------- #
async def start_new_round(session: Session):
    """Start a new trivia round"""
    q = game.choose_random_question(session)
    if not q:
        await manager.broadcast({
            "type": "game_over",
            "message": "No questions available!",
            "scores": game.get_sorted_scores()
        })
        game.reset_game()
        return

    await manager.broadcast({
        "type": "new_question",
        "question": q.front,
        "options": game.question_options,
        "round": game.round_number + 1,
        "total_rounds": game.max_rounds
    })


async def end_game():
    """End the current game and show results"""
    game.game_active = False
    sorted_scores = game.get_sorted_scores()
    
    winner_msg = "Game over!"
    if sorted_scores:
        winner = sorted_scores[0]
        if len(sorted_scores) > 1 and sorted_scores[0][1] == sorted_scores[1][1]:
            winner_msg = f"It's a tie! Both scored {winner[1]} points!"
        else:
            winner_msg = f"🏆 {winner[0]} wins with {winner[1]} points!"
    
    await manager.broadcast({
        "type": "game_over",
        "message": winner_msg,
        "scores": sorted_scores
    })
    
    # Reset for next game
    game.ready_players.clear()
    game.answered_this_round.clear()
    game.current_question = None
    game.round_number = 0
    
    await asyncio.sleep(3)
    
    # Return to lobby
    await manager.broadcast({
        "type": "return_to_lobby",
        "message": "Returning to lobby..."
    })