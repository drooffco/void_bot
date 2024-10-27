import discord
import re
from openskill.models.weng_lin.plackett_luce import PlackettLuce, PlackettLuceRating
import mysql.connector
import mysql.connector.cursor
from test_ranking import connect_to_mysql

async def get_teams_from_channel(channel: discord.TextChannel) -> str:
    teams_list = []
    
    # TODO: figure out a way to skip the first message
    async for message in channel.history(limit=1000):
        teams_list.append(message)

    ranked_teams = create_teams(teams_list)
    # TODO: Find number of lobbies based on amount of users signed up

    # TODO: Find who is in each lobby based on the high/low priority status

    # TODO: Return string with teams chunked into lobby(s) 


def create_teams(team_list: list[discord.Message]) -> dict:
    # Create the list of all the users
    user_id_list = create_user_id_list()

    # Get the player if they exist based on their discord id in the user mentions of the message
    player_ratings_dict = get_existing_players_rating_by_discord_id(team_list)
    
    # If the player doesn't exist make a new rating for them and flag their nidhash as -1 and populate
    #   their latest_username column for searching on the backend
    player_ratings_dict = make_new_player_ratings(player_ratings_dict, user_id_list)

    # Create a team rank by averaging out the rank of the players
    ranked_teams = create_ranked_teams_from_player_ranks(team_list, player_ratings_dict)

    return ranked_teams


def create_ranked_teams_from_player_ranks(team_list: list[discord.Message], player_ratings_dict: dict[int, float]) -> list[str, float]:
    team_rating_list = []
    for message in team_list:
        team_name = message.content.split(f' ')[0]
        team_rating = 0
        for mention in message.mentions:
            team_rating += player_ratings_dict[mention.id]

        team_rating_list.append(team_name, team_rating)

    team_rating_list.sort(lambda x: x[1], reverse=True)
    return team_rating_list


def create_user_id_list(team_list: list[discord.Message]) -> list[tuple[int, str]]:
    user_id_list = []
    for message in team_list:
        user_id_list.extend(get_team_from_message(message))
    return user_id_list


def get_team_from_message(message: discord.Message) -> list[tuple[int, str]]:
    # Define the pattern for extracting gamer tags
    pattern = r'@(\w+)\s+(\S+)'

    # Find all matches for mentions and gamer tags
    matches = re.findall(pattern, message.content)

    # Create a list of tuples with user IDs and gamer tags
    result = []
    for mention in message.mentions:
        # Find the corresponding gamer tag
        for match in matches:
            if mention.name == match[0]:  # Check if the mention matches the username
                result.append((mention.id, match[1]))

    return result


def make_new_player_ratings(player_ratings_dict, user_id_list) -> dict[int, float]:
    connection, cursor = connect_to_mysql()
    cursor.executemany(
        """
            INSERT INTO PLAYER_RATING (DISCORD_USER_ID, APEX_ID, LATEST_USERNAME, PLAYER_RATING, PLAYER_RATING_VOLATILITY) 
            VALUES(?, ?, ?, ?, ?)
        """,
        [
            (user_id, str(-1), gamer_tag, 25.0, 25.0/3.0) for user_id, gamer_tag in user_id_list if user_id not in player_ratings_dict
        ]
    )

    cursor.close()
    connection.close()

    for user_id, gamer_tag in user_id_list:
        if user_id not in player_ratings_dict:
            player_ratings_dict[user_id] = 25.0
        
    return player_ratings_dict


def get_existing_players_rating_by_discord_id(team_list: list[discord.Message]) -> dict[str, float]:
    if len(team_list) == 0:
        return {}
    
    connection, cursor = connect_to_mysql()
    cursor.execute(
        f"""
        SELECT * 
        FROM PLAYER_RATING
        WHERE {'OR'.join([f"DISCORD_USER_ID='{mention.id}'" for message in team_list for mention in message.mentions])};
        """
    )

    player_ratings = cursor.fetchall()
    cursor.close()
    connection.close()

    existing_player_dict = {}

    for player in player_ratings:
        _, discord_user_id, apex_id, _, mu, _= player
        if int(apex_id) != -1:
            existing_player_dict[str(discord_user_id)] = mu

    return existing_player_dict


if __name__ == '__main__':
    get_teams_from_channel()
