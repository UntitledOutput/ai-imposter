# AI-Imposter

A lightweight Python implementation of a multiplayer social-deduction style game (Impostor-style) that bridges WebSocket clients and an AI-driven player backend over a TCP socket. The repository contains a WebSocket server (client.py), game logic (game.py) and Pydantic message models (models.py).

This README documents how the components interact, how to run the server, the message protocol, and recommended next steps.

## Features
- WebSocket server that accepts client connections and maps them into a Game instance.
- Game loop and turn/vote management implemented in `game.py`.
- A simple protocol using message prefixes and JSON payloads defined by Pydantic models in `models.py`.
- Integration point for an AI player backend reached over a TCP socket.

## Requirements
- Python 3.10+

Dependencies used by the code:
- websockets
- pydantic
- colorama
- faker

Install dependencies with pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install websockets pydantic colorama faker
```

Or add them to a `requirements.txt` and install with `pip install -r requirements.txt`.

## Quick start — run the WebSocket server
By default `client.py` starts a WebSocket server. Run:

```bash
python client.py
```

The file currently prints:

```
[*] WebSocket server running on ws://192.168.1.242:8765
```

Which corresponds to:
- WebSocket host: 192.168.1.242
- WebSocket port: 8765

Note: these values are hard-coded in `client.py` and `game.py`. You will likely want to change them to your host interface or make them configurable via environment variables. See "Configuration" below.

## Architecture & connections
- Web clients connect to the WebSocket server implemented in `client.py`.
- On a `setup` message, the server constructs a `Game` instance (game.py) and may connect to an AI backend.
- `Game` opens a TCP connection to an AI player server using host `192.168.1.196`, port `2026` (hard-coded in `Game.__init__`).
- When a player slot has no socket (i.e., an AI will play that slot), the server sends/receives JSON messages to/from the AI backend over the TCP socket.

If you do not have an AI backend ready, you can:
- Run a stub TCP server that reads JSON requests and returns valid JSON responses (matching the Pydantic models), or
- Modify `game.py` to bypass the TCP connection for local human-only play.

## Message protocol (WebSocket messages)
Messages are plain text with the format:

```
<type>/<json-payload>
```

Where `<type>` is one of:
- `setup` — initialize a game from a client
- `response` — a player response during play
- `vote` — a voting response

All JSON payloads must match the shapes defined in `models.py`.

### Example: SetupRequest (client -> server)
Type: `setup`

JSON payload example:

```json
{
  "id": "client123",
  "player_count": 4,
  "impostor_count": 1,
  "word": "Apple",
  "hint": "Red"
}
```

Sent as a single WebSocket message:

```
setup/{"id":"client123","player_count":4,"impostor_count":1,"word":"Apple","hint":"Red"}
```

### Example: Response (client -> server)
Type: `response`

JSON payload example:

```json
{
  "word": "banana",
  "start_vote": false
}
```

Sent as:

```
response/{"word":"banana","start_vote":false}
```

- `word` should be a single cleaned token (game cleans non-alpha characters and drops short tokens).
- `start_vote` should be set to true only when the player wants to initiate the voting process.

### Example: VotingResponse (client -> server)
Type: `vote`

JSON payload example:

```json
{
  "suspect": "Alice"
}
```

Sent as:

```
vote/{"suspect":"Alice"}
```

### Example: Server -> Client messages
The server constructs messages similarly using the same `<type>/<json>` format. Look in `game.py` for examples of:
- `setup` / `spec_setup` (setup responses)
- `play` (cycle/play prompt)
- `vote` (voting requests)
- `post_vote` (end-of-game voting results)

The JSON shapes follow the Pydantic models in `models.py`:
- `SetupResponse`, `SpectateSetupResponse`, `CycleResponse`, `PostVoteResponse`, etc.

## Running a simple test client
You can test the WebSocket server using `websocat`, a browser client, or a small Python client using `websockets`.

Example (websocat):

```bash
websocat ws://192.168.1.242:8765
# then type:
setup/{"id":"tester","player_count":3,"impostor_count":1,"word":"Apple","hint":"Red"}
```

Example Python test snippet:

```python
import asyncio
import websockets
async def run():
    uri = "ws://192.168.1.242:8765"
    async with websockets.connect(uri) as ws:
        await ws.send('setup/{"id":"t1","player_count":3,"impostor_count":1,"word":"Apple","hint":"Red"}')
        async for msg in ws:
            print(msg)

asyncio.run(run())
```

## Configuration and recommended improvements
Currently, IP addresses and ports are hard-coded:
- WebSocket server in `client.py`: `("192.168.1.242", 8765)`
- AI TCP backend in `game.py`: `('192.168.1.196', 2026)`

Recommended changes:
- Make host and port configurable (via CLI args or environment variables).
- Add a `requirements.txt`.
- Add error handling and reconnection logic for the AI backend.
- Consider switching to structured logging instead of print statements.
- Add unit tests for `clean_word` and core Game flows.
- Make socket timeouts and buffer sizes configurable.

## Development
- Consider using `black` and `flake8` for code style.
- Add pytest tests under `tests/`.
- Add `pre-commit` hooks to automate formatting and linting.

## Contributing
1. Fork the repository.
2. Create a topic branch.
3. Make changes with tests.
4. Open a Pull Request describing your changes.

## License
No license file is present in the repository. Add a LICENSE file (for example MIT) if you want to make this project open-source.

## Contact / Issues
Open issues on GitHub for bugs, feature requests, or help running the project.
