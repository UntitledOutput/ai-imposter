import websockets
import time
from colorama import Fore, Back, Style, init
import threading
import asyncio

from models import *
from game import *

init(autoreset=True)

async def handle_client(websocket):
    print(f"[+] Connected: {websocket.remote_address}")

    game = Game()

    try:
        async for message in websocket:

            type = message.split("/", 1)[0]
            payload = message.split("/", 1)[1]

            print(f"Received message of type '{type}' from {websocket.remote_address}")

            if (type == "setup"):
                request = SetupRequest.model_validate_json(payload)

                print(f"Received setup from {websocket.remote_address}:")
                game.setup(request.player_count, request.impostor_count, request.word, request.hint)
                game.is_spectator = True
                game.player_socket = ClientSocket(websocket)
                #game.players[0].id = request.id
                #game.players[0].socket = websocket
                await game.start()

            if (type == "response"):
                response = Response.model_validate_json(payload)
                await game.handle_player_response(response, 0)

            if (type == "vote"):
                voting_response = VotingResponse.model_validate_json(payload)
                game.receive_vote_response(voting_response, 0)
                await game.check_votes()
                
                
    except Exception as e:
        print(f"[!] Error with {websocket.remote_address}: {e}")
    finally:
        print(f"[-] Disconnected: {websocket.remote_address}")

async def main():
    print("[*] WebSocket server running on ws://192.168.1.242:8765")
    async with websockets.serve(handle_client, "192.168.1.242", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())