from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Client, Message
from responses import get_response
from directory_root import ROOT_DIR
from settings.project_secrets import DISCORD_TOKEN
from test_ranking import rank_lobby_matches




intents: Intents = Intents.default()
intents.message_content = True
client: Client =  Client(intents=intents)

async def send_message(message: Message, user_message: str) -> None:
    if not user_message:
        print('Message was empty because intetnts were not enabled')

    if is_private := user_message[0] == '?':
        user_message = user_message[1:]

    try:
        response: str = get_response(user_message)
        await message.author.send(response) if is_private else await message.channel.send(response)
    except Exception as e:
        print(e)


@client.event
async def on_read() -> None:
    print(f'{client.user} is now running')


@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return
    
    if '!rank' in message.content:
        await handle_rank_request(message)


    print(f'that didnt quite work try again')
    # await send_message(message, user_message)


async def handle_rank_request(message: Message) -> None:
    request = message.content.split(' ')
    if len(request) > 4:
        raise ValueError('Your rank request contained too many values please try again with the format !rank $LOBBY $NUMBER_OF_MATCHES')

    if len(request) == 3:
        response_text = rank_lobby_matches(request[1], int(request[2]))
    elif len(request) == 4:
        response_text = rank_lobby_matches(request[1], int(request[2]), bool(request[3]))

    response_list = split_string_by_newline(response_text, 1999)
    for response in response_list:
        await message.channel.send(response)


def split_string_by_newline(s, max_length=2000) -> list[str]:
    result = []
    
    while len(s) > max_length:
        # Get the substring up to the max length
        substring = s[:max_length]
        
        # Find the last newline character in the substring
        last_newline_index = substring.rfind('\n')
        
        if last_newline_index == -1:
            # If no newline is found, break at max_length (this can be changed based on preferences)
            result.append(substring)
            s = s[max_length:]
        else:
            # Split at the last newline and append to result
            result.append(s[:last_newline_index])
            s = s[last_newline_index+1:]  # Continue with the rest of the string
    
    # Append the remaining part of the string
    result.append(s)
    
    return result


def main() -> None:
    client.run(token=DISCORD_TOKEN)


if __name__ == '__main__':
    main()
    