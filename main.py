from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dataclasses import dataclass
from typing import Dict
import uuid
import json
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import datetime  # For accurate timestamps
from pymongo import MongoClient  # For MongoDB integration

templates = Jinja2Templates(directory="templates")



@dataclass
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict = {}

        # Connect to MongoDB
        self.client = MongoClient("mongodb://localhost:27017/chat_app")  
        self.db = self.client["chat_app"]
        self.chat_messages = self.db["chat_messages"]

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        id = str(uuid.uuid4())
        self.active_connections[id] = websocket

        await self.send_message(
            websocket,
            json.dumps(
                {
                    "isMe": True,
                    "data": "Have joined!!",
                    "username": "You",
                }
            ),
        )

    async def send_message(self, ws: WebSocket, message: str):
        await ws.send_text(message)

    def find_connection_id(self, websocket: WebSocket):
        websocket_list = list(self.active_connections.values())
        id_list = list(self.active_connections.keys())

        pos = websocket_list.index(websocket)
        return id_list[pos]

    async def broadcast(self, webSocket: WebSocket, data: str):
        decoded_data = json.loads(data)

        # Save message to MongoDB
        message = {
            "message": decoded_data["message"],
            "username": decoded_data["username"],
            "timestamp": datetime.datetime.now(),  # Use datetime for accuracy
        }
        self.chat_messages.insert_one(message)

        for connection in self.active_connections.values():
            is_me = False
            if connection == webSocket:
                is_me = True

            await connection.send_text(
                json.dumps(
                    {
                        "isMe": is_me,
                        "data": decoded_data["message"],
                        "username": decoded_data["username"],
                    }
                )
            )

    def disconnect(self, websocket: WebSocket):
        id = self.find_connection_id(websocket)
        del self.active_connections[id]

        return id

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
connection_manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
def get_room(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/message")
async def websocket_endpoint(websocket: WebSocket):
    # Accept the connection from the client.
    await connection_manager.connect(websocket)

    try:
        while True:
            # Receives message from the client
            data = await websocket.receive_text()
            await connection_manager.broadcast(websocket, data)
    except WebSocketDisconnect:
        id = await connection_manager.disconnect(websocket)
        return RedirectResponse("/")

@app.get("/join", response_class=HTMLResponse)
def get_room(request: Request):
    return templates.TemplateResponse("room.html", {"request": request})

analytics_pipeline = [
    # Stage 1: Match relevant documents based on your criteria (if needed)
    {
        "$match": {
            "sender": "username"
        }
    },

    # Stage 2: Group by sender and calculate total messages
    {
        "$group": {
            "_id": "$sender",
            "totalMessages": {"$sum": 1}
        }
    },

    # Stage 3: Sort the results based on totalMessages
    {
        "$sort": {"totalMessages": -1}
    }
]

# Execute the aggregation pipeline
result = list(messages_collection.aggregate(analytics_pipeline))

# Display the result
for user_stats in result:
    print(f"User: {user_stats['_id']}, Total Messages: {user_stats['totalMessages']}")
