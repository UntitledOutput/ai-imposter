from pydantic import BaseModel, Field

class Response(BaseModel):
    word: str = Field(description="The single word that the player would say in the game, based on their role and the current state of the game. Do not include any additional text or explanation, just the word itself.")
    start_vote: bool = Field(default=False, description="Set to true ONLY if you are highly confident you know who the imposter is and want to start a vote. Only start a vote well into the game (after the first few rounds). Default to false if unsure.")

class VotingResponse(BaseModel):
    suspect: str = Field(description="The name of the player you suspect to be the imposter.")

class SetupResponse(BaseModel):
    player_count: int
    role: str
    word: str
    players: list[str]

class SpectateSetupResponse(BaseModel):
    player_count: int
    players: list[str]
    word: str
    impostors: list[str]

class PostVoteResponse(BaseModel):
    vote_result: str
    imposter: str
    vote_per_player: list[str]

class CycleResponse(BaseModel):
    id: str
    word: str


class Request(BaseModel):
    role: str
    words: list[str]
    hint: str
    id: str
    turn: int
    type: str

class ChatRequest(BaseModel):
    role: str
    words: list[str] 
    player_words: dict[str, list[str]] = {} 
    hint: str
    id: str
    turn: int
    type: str

class SetupRequest(BaseModel):
    id: str
    player_count: int
    impostor_count: int
    word: str
    hint: str

    

