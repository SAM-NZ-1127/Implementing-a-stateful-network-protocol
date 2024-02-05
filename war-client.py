#  HWK - 3 - Implementing a stateful network protocol : WAR GAME
# Shivam Jayeshkumar Mehta
# Client-Side

import asyncio
from enum import Enum
import logging
import sys

# Values used to control game play states
class Command(Enum):
    WANT_GAME = 0
    GAME_START = 1
    PLAY_CARD = 2
    PLAY_RESULT = 3

# Result of the game
class Result(Enum):
    WIN = 0
    DRAW = 1
    LOSE = 2

#read the the number of bytes bytes from socket
def readexactly(sock, num_bytes):
    data = b''
    while len(data) != num_bytes:
        current = sock.recv(1)
        data += current
        if len(current) == 0 and len(data) != num_bytes:
            print('THERE IS AN ERROR.')
            sock.close()
            return
    return data

# Limit no. of clients  that can connect to the server at a time
async def limit_client(host, port, sem):
    async with sem:
        return await client(host, port)


async def client(host, port):
    try:
        reader, writer = await asyncio.open_connection(host, port)
        score = 0
        writer.write(b"\0\0")
        card_message = await reader.readexactly(27)
        for card in card_message[1:]:
            writer.write(bytes([Command.PLAY_CARD.value, card]))
            result = await reader.readexactly(2)
            if result[1] == Result.WIN.value:
                score += 1
            elif result[1] == Result.LOSE.value:
                score -= 1
        if score > 0:
            result = "won"
        elif score < 0:
            result = "lost"
        else:
            result = "drew"
        print("Result: ", result)
        logging.debug("Game complete, I %s", result)
        writer.close()
        return 1
    except ConnectionResetError:
        logging.error("ConnectionResetError")
        return 0
    except asyncio.streams.IncompleteReadError:
        logging.error("asyncio.IncompleteReadError")
        return 0
    except OSError:
        logging.error("OSError")
        return 0
loop = asyncio.get_event_loop()

#main function
def main(args):
    host = args[0]
    port = int(args[1])
    loop.run_until_complete(client(host, port))
    loop.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])