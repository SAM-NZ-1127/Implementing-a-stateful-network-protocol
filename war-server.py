#  HWK - 3 - Implementing a stateful network protocol : WAR GAME
# Shivam Jayeshkumar Mehta
# Server-Side

import asyncio
from collections import namedtuple
from enum import Enum
import logging
import random
import sys
logging.basicConfig(level=logging.WARNING) #debug warning

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

# list to keep track of clients
paired_clients = list()

#namedtuple to keep track of each clients game state
Game = namedtuple("Game", ["p1", "p2"])

#close the game
def end(s1, s2):
    s1.close()
    s2.close()
    pass

#compare cards of two clients
def compare_cards(card1, card2):
    first_card = card1 % 13
    second_card = card2 % 13
    if first_card < second_card:
        return 2
    elif first_card == second_card:
        return 1
    else:
        return 0

#function to send 26 cards out of 52 to each clients
def deal_cards():
    deck_size = 52
    deck = [index for index in range(deck_size)]
    random.shuffle(deck)
    first_hand = []
    second_hand = []
    while len(deck) > 0:
        dealt_card = deck.pop()
        if len(first_hand) < 26:
            first_hand.append(dealt_card)
        else:
            second_hand.append(dealt_card)
    both_hands = [first_hand, second_hand]
    return both_hands

#Verify if the card provided is not part of the deck then return error
def check_card(card, deck):
    if card not in deck:
        return False
    return True

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

#Game Logic
async def handle_game(f_client, s_client):
    split_deck = deal_cards()
    c1_cards = split_deck[0]
    c2_cards = split_deck[1]
    c1_used = [False] * 26
    c2_used = [False] * 26
    try:
        f_client_data = await f_client[0].readexactly(2)
        s_client_data = await s_client[0].readexactly(2)
        if(f_client_data[1] != 0) or s_client_data[1] != 0:
            print('ERROR... User does not enter in 0 for the first time')
            end(f_client[1], s_client[1])
            end(f_client[1].get_extra_info('socket'),
                    s_client[1].get_extra_info('socket'))
            return
        f_client[1].write(bytes(([Command.GAME_START.value]+c1_cards)))
        s_client[1].write(bytes(([Command.GAME_START.value]+c2_cards)))
        total_turns = 0
        while total_turns < 26:
            f_client_data = await f_client[0].readexactly(2)
            s_client_data = await s_client[0].readexactly(2)
            if f_client_data[0] != 2 and s_client_data[0] != 2:
                print('Error... User does not enter in 2.')
                end(f_client[1], s_client[1])
                end(f_client[1].get_extra_info('socket'),
                        s_client[1].get_extra_info('socket'))
                return
            if check_card(f_client_data[1], split_deck[0]) is False\
                    or check_card(s_client_data[1], split_deck[1]) is False:
                print('Error... A clients card does not match card dealt')
                end(f_client[1], s_client[1])
                end(f_client[1].get_extra_info('socket'),
                        s_client[1].get_extra_info('socket'))
                return
            for x in range(0, 26):
                if f_client_data[1] == c1_cards[x] or \
                        s_client_data[1] == c2_cards[x]:
                    if f_client_data[1] == c1_cards[x]:
                        if c1_used[x] is False:
                            c1_used[x] = True
                        else:
                            print('Error: A client tried to use '
                                'the same card again ')
                            end(f_client[1], s_client[1])
                            end(f_client[1].get_extra_info('socket'),
                                    s_client[1].get_extra_info('socket'))
                            return
                    if s_client_data[1] == c2_cards[x]:
                        if c2_used[x] is False:
                            c2_used[x] = True
                        else:
                            print('Error: A client tried to use '
                                'the same card again ')
                            end(f_client[1], s_client[1])
                            end(f_client[1].get_extra_info('socket'),
                                    s_client[1].get_extra_info('socket'))
                            return
            c1_result = compare_cards(f_client_data[1], s_client_data[1])
            c2_result = compare_cards(s_client_data[1], f_client_data[1])
            c1_send_result = [Command.PLAY_RESULT.value, c1_result]
            c2_send_result = [Command.PLAY_RESULT.value, c2_result]
            f_client[1].write(bytes(c1_send_result))
            s_client[1].write(bytes(c2_send_result))
            total_turns += 1
        end(f_client[1], s_client[1])
        end(f_client[1].get_extra_info('socket'),
                s_client[1].get_extra_info('socket'))
    except ConnectionResetError:                                   #Error handling
        logging.error("ConnectionResetError")
        return 0
    except asyncio.streams.IncompleteReadError:
        logging.error("asyncio.streams.IncompleteReadError")
        return 0
    except OSError:
        logging.error("OSError")
        return 0

# pair the two  clients
async def pair_clients(reader, writer):
    for clients in paired_clients:
        if clients[1] is None:
            clients[1] = (reader, writer)
            await handle_game(clients[0], clients[1])
            clients[0][1].close()
            clients[1][1].close()
            paired_clients.remove(clients)
            return
    paired_clients.append([(reader, writer), None])

# Setting up the server and handle for connections with the client.
def serve_game(host, port):
    loop = asyncio.get_event_loop()
    co_routine = asyncio.start_server(pair_clients, host, port)
    server = loop.run_until_complete(co_routine)
    print('SERVER: {}'.format(server.sockets[0].getsockname()))
    try:                   #run the game until the user presses ctrl + c to end the game.
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()

#main function
def main(args):
    host = '127.0.0.1' #default host
    port = int(args[0])
    try:
        serve_game(host, port)
    except KeyboardInterrupt:
        pass
    return

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])