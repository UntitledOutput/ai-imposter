import asyncio
import math
import random
import hashlib
from colorama import Fore, Back, Style, init
import socket
from faker import Faker
import websockets
from websockets.asyncio.client import ClientConnection

import re

def clean_word(word: str) -> str:
    word = re.sub(r'[^a-zA-Z]', ' ', word)
    words = [w for w in word.split() if len(w) > 1]
    return words[0] if words else ""

from models import *

class ClientSocket:
    def __init__(self, socket: ClientConnection):
        self.socket = socket

    async def send_to_socket(self, message_type: str, content: str):
        try:
            print(f"Sending message of type '{message_type}' to {self.socket.remote_address}")
            message = f"{message_type}/{content}"
            await self.socket.send(message)
        except Exception as e:
            print(f"Failed to send message: {e}")

class Player:
    def __init__(self):
        self.role = "normal"
        self.id = ""
        self.word = ""
        self.socket: ClientConnection  | None = None

        self.words_said = []

    def setup_as_impostor(self, word: str):
        self.role = "Impostor"
        self.word = word

    async def send_to_socket(self, message_type: str, content: str):
        if not self.socket:
            print(f"Error: No socket assigned to player {self.id}")
            return

        try:
            message = f"{message_type}/{content}"
            await self.socket.send(message)
            #print(f"Success: Sent to {self.id}")
            
        except Exception as e:
            print(f"Failed to send to {self.id}: {e}")


class GuessedWord:
    def __init__(self, player, word):
        self.player:Player = player
        self.word = word

    def serialize(self):
        return f"{self.player.id} said: {self.word}"

class Game:
    def __init__(self):

        self.turn = 0
        self.round = 0
        self.impostor = 0
        self.word = "Apple"
        self.hint = "Red"
        self.words = []

        self.suspects = []

        self.ai_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ai_socket.settimeout(30)
        self.player_socket: ClientSocket  | None = None

        self.is_spectator = False


        server_address = ('192.168.1.196', 2026)
        print(f'Connecting to {server_address[0]} port {server_address[1]}')
        self.ai_socket.connect(server_address)

    def setup(self, player_count, impostor_count, word="Apple", hint="Red"):
        self.players = [Player() for i in range(player_count)]
        self.impostor_count = impostor_count
        self.word = word
        self.hint = hint

    async def start(self):

        impostor_count = 0

        print(f"Starting game with {len(self.players)} players and {self.impostor_count} impostors.")

        print(f"The word is: {self.word} and the hint is: {self.hint}")

        self.impostor = random.randint(0, len(self.players)-1)

        self.suspects = ["" for i in range(len(self.players))]
        self.words = []

        fake = Faker()

        names = [fake.first_name() for _ in range(len(self.players))]

        while len(set(names)) < len(names):
            seen = set()
            for idx, name in enumerate(names):
                if name in seen:
                    names[idx] = fake.first_name()
                else:
                    seen.add(name)

        for i in range(len(self.players)):
            if (self.players[i].socket is None):
                self.players[i].id = names[i]

        for i in range(0,len(self.players)):
            p = self.players[i]

            p.words_said = []

            p.word = self.word
            if (impostor_count < self.impostor_count):
                if (i == self.impostor):
                    impostor_count += 1
                    p.setup_as_impostor(self.hint)
                    print(f"Player {p.id} is the impostor!")

    
        if (not self.is_spectator):
            p = self.players[0]
            if (p.socket is not None):
                print(f"Sending setup to {p.id} at {p.socket.remote_address}")
                content = SetupResponse(player_count=len(self.players), role=p.role, word=p.word, players=[player.id for player in self.players]).model_dump_json()
                await p.send_to_socket("setup",content)
        elif self.player_socket is not None:
            content = SpectateSetupResponse(player_count=len(self.players), players=[player.id for player in self.players], word=self.word, impostors=[player.id for player in self.players if player.role == "Impostor"]).model_dump_json()
            await self.player_socket.send_to_socket("spec_setup",content)

        await self.cycle()

    async def handle_voting_process(self, starting_player):
        print(f"{self.players[starting_player].id} has started a vote!")
        voting_requests = self.start_vote()
        for i in range(len(voting_requests)):
            if self.players[i].socket is not None:
                content = voting_requests[i].model_dump_json()
                await self.players[i].send_to_socket("vote",content)
            else:
                self.ai_socket.sendall(voting_requests[i].model_dump_json().encode())
                data = self.ai_socket.recv(1024)
                if not data:
                    print('No data received. Closing connection.')
                    break
                voting_response = VotingResponse.model_validate_json(data)
                self.receive_vote_response(voting_response, i)
        if self.player_socket is not None:
            await self.check_votes()

    async def handle_player_response(self, response: Response, index:int):

        print(f"Received response from {self.players[index].id}: {response.word}, start_vote: {response.start_vote}")

        self.receive_response(response)

        if response.start_vote:
            await self.handle_voting_process(index)
            return

        await self.cycle()

    async def cycle(self):
        while True:
            if (self.players[self.turn].socket is None):
                print(f"Waiting for response from {self.players[self.turn].id}...")
                repeat = True

                if self.player_socket is not None:
                    await self.player_socket.send_to_socket("pre_play",CycleResponse(id=self.players[self.turn].id, word="Thinking..").model_dump_json())


                await asyncio.sleep(1.5)



                while repeat:
                    repeat = False
                    request = self.send_request()
                    id = request.id

                    self.ai_socket.sendall(request.model_dump_json().encode())


                    data = self.ai_socket.recv(1024)
                    if not data:
                        print('No data received. Retrying')
                        repeat = True
                        continue
                    response = Response.model_validate_json(data)



                    if not self.receive_response(response):
                        repeat = True
                    else:
                        if (len(response.word) == 0):
                            response.word = "No response"
                            if (response.start_vote and self.round > 0) or self.round > 3:
                                response.word = "STARTVOTE"
                        print(f"Sending response to {self.players[0].id}")
                        if self.player_socket is not None:
                            await self.player_socket.send_to_socket("play",CycleResponse(id=id, word=response.word).model_dump_json())


    
                if ((response.start_vote and self.round > 0) or self.round > 3):
                    print(f"{request.id} has started a vote!")

                    await self.handle_voting_process(self.turn)
                    break


                await asyncio.sleep(1.5) 


            else:
                print(f"Waiting for response from {self.players[self.turn].id}...")
                await self.players[self.turn].send_to_socket("play",CycleResponse(id=self.players[self.turn].id, word="").model_dump_json())


                break


    def send_request(self) -> ChatRequest:

        words = [w.serialize() for w in self.words]

        r = ChatRequest(role=self.players[self.turn].role.lower(), words=words, hint=self.players[self.turn].word, id=self.players[self.turn].id, turn=self.round, type="play")

        for player in self.players:
            r.player_words[player.id] = player.words_said

        return r

    def start_vote(self) -> list[ChatRequest]:
        print(f"{Fore.YELLOW}Starting vote!{Style.RESET_ALL}")

        words = [w.serialize() for w in self.words]

        r = [ChatRequest(role=p.role.lower(), words=words, hint=p.word, id=p.id, turn=self.round, type="vote") for p in self.players]
        for player in self.players:
            for _r in r:
                _r.player_words[player.id] = player.words_said

        return r

    def receive_vote_response(self, response: VotingResponse, index:int):
        self.suspects[index] = response.suspect

    async def check_votes(self):

        for i in range(len(self.players)):
            print(f"{self.players[i].id} voted for {self.suspects[i].upper()}")

        print("Calculating votes...")

        vote_count = {}
        for suspect in self.suspects:
            if suspect.upper() not in vote_count:
                vote_count[suspect.upper()] = 0
            vote_count[suspect.upper()] += 1
        
        max_votes = max(vote_count.values())

        suspects_with_max_votes = [suspect for suspect, count in vote_count.items() if count == max_votes]
        if len(suspects_with_max_votes) > 1:
            print(f"Tie between {', '.join(suspects_with_max_votes)}.")
        
        print(f"Suspects with the most votes: {', '.join(suspects_with_max_votes)}")

        if self.players[self.impostor].id.upper() in suspects_with_max_votes:
            print(f"{Fore.GREEN}The impostor {self.players[self.impostor].id} was caught!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}The impostor {self.players[self.impostor].id} was not caught!{Style.RESET_ALL}")

        vote_per_player = [self.suspects[i].upper() for i in range(len(self.players))]
        print(f"Vote results: {vote_per_player}")
        if self.player_socket is not None:

            result = ""
            if self.players[self.impostor].id.upper() in suspects_with_max_votes:
                result = "win"
                if (len(suspects_with_max_votes) > 1):
                    result = "tie"
            else:
                result = "lose"

            pv_response = PostVoteResponse(vote_result=result, imposter=self.players[self.impostor].id, vote_per_player=vote_per_player)



            await self.player_socket.send_to_socket("post_vote", pv_response.model_dump_json())
            await asyncio.sleep(2.5)
            await self.player_socket.socket.close()

    def receive_response(self, response: Response) -> bool:
        response.word = clean_word(response.word)

        if len(response.word) == 0:
            print("Player returned an empty word.")
            #print(response)
            if response.start_vote:
                print("Player also started a vote.")
                return True
            return False

        self.words.append(GuessedWord(self.players[self.turn], response.word))

        msg = ""



        if self.players[self.turn].role == "impostor":
            msg += (f"{Fore.RED}{self.players[self.turn].id} said {response.word}{Style.RESET_ALL}")
        else:
            msg += (f"{self.players[self.turn].id} said {response.word}{Style.RESET_ALL}")

        print(msg)

        self.turn = (self.turn + 1) % len(self.players)

        if self.turn == 0:
            self.round += 1
            print(f"--- End of Round {self.round} ---")

        return True
