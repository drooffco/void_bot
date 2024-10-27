from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Client, Message
from responses import get_response
from directory_root import ROOT_DIR
from settings.project_secrets import DISCORD_TOKEN
from test_ranking import rank_lobby_matches
from read_channel_messages import get_teams_from_channel


intents: Intents = Intents.default()
intents.message_content = True
client: Client =  Client(intents=intents)


@client.event
async def on_read() -> None:
    print(f'{client.user} is now running')


@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return
    
    try:
        
        if '!rank' in message.content:
            await handle_rank_request(message)

        if '!create_scrim_lobbies' in message.content:
            await handle_create_scrim_lobbies(message)
    except ValueError as e:
        await message.channel.send(f'Looks like that command didnt quite work ;( this was the problem:\n{e}')


    print(f'that didnt quite work try again')
    # await send_message(message, user_message)


def handle_create_scrim_lobbies(message: Message) -> None:
    request = message.content.split(' ')

    if len(request) > 2:
        raise ValueError('Your rank request contained too many values please try again with the format !create_scrim_lobbies $CHANNEL_NAME')
    
    if not message.channel_mentions or len(message.channel_mentions) > 1:
        raise ValueError('You must attach ONE channel in this command')
    
    teams = get_teams_from_channel(message.channel_mentions[0])
    send_response_to_channel(response_text=teams, message=message)


def handle_rank_request(message: Message) -> None:
    request = message.content.split(' ')
    if len(request) > 4:
        raise ValueError('Your rank request contained too many values please try again with the format !rank $LOBBY $NUMBER_OF_MATCHES')

    if len(request) == 3:
        response_text = rank_lobby_matches(request[1], int(request[2]))
    elif len(request) == 4:
        response_text = rank_lobby_matches(request[1], int(request[2]), bool(request[3]))

    send_response_to_channel(response_text=response_text, message=message)


async def send_response_to_channel(response_text: str, message: Message):
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
    