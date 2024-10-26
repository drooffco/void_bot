import json
import mysql.connector

import numpy as np

import mysql.connector.cursor
from openskill.models.weng_lin.plackett_luce import PlackettLuce, PlackettLuceRating
from settings.project_secrets import STATS_KEYS, mysql_creds
from requests import get
from src.utils.scoring_utils import PLACEMENT_POINTS_DICT


def rank_lobby_matches(lobby: str, series_length: int = 6, print_players: bool = False):
    # Get the data from the lobby and make the teams for that match
    # Initailize the ranking engine
    rating_model = PlackettLuce()

    match_results_json = get_lobby_match_history_json(lobby)
    
    for match_number in range(1, series_length + 1):
        teams_and_players_dict, nid_to_players_dict, match = make_teams_from_match(match_results_json, match_number, series_length)

        # If there are less than 45 players in the games or the game was reset
        if teams_and_players_dict == None and nid_to_players_dict == None:
            continue

        # Get existing player rating dict
        existing_player_rating_dict = get_existing_player_rating_dict(rating_model)

        # Make the rating for the players
        teams_to_rating_dict = {}
        for team in teams_and_players_dict:
            teams_to_rating_dict[team] = make_new_player_list(
                rating_model=rating_model,
                players=teams_and_players_dict[team],
                existing_player_rating_dict=existing_player_rating_dict
            )

        # print_teams_rating(teams_to_rating_dict)

        teams_list = list(teams_to_rating_dict.keys())
        team_score_list = get_team_score_list(teams_list, match)

        # Get the new ratings of the players after that match
        rating_model.rate(
            teams=list(teams_to_rating_dict.values()),
            scores=team_score_list,
        )
        
        update_players_rating_db(list(teams_to_rating_dict.values()), nid_to_players_dict)
    
    return get_teams_rating_str(teams_to_rating_dict, print_players)


def update_players_rating_db(players_list: list[list[PlackettLuceRating]], nid_to_players_dict: dict[str, str]) -> None:
    for players in players_list:
        for player in players:
            if player_exists_in_db(player):
                # Update the current player
                update_player_db_rating(player, nid_to_players_dict)
            else:
                # Add new player
                add_player_db_rating(player, nid_to_players_dict)



def add_player_db_rating(player: PlackettLuceRating, nid_to_players_dict: dict[str, str]) -> None:
    connection, cursor = connect_to_mysql()

    cursor.execute(
        f"""
        INSERT INTO PLAYER_RATING (DISCORD_USER_ID, APEX_ID, LATEST_USERNAME, PLAYER_RATING, PLAYER_RATING_VOLATILITY)
        VALUES (-1, '{player.name}', '{nid_to_players_dict[player.name]}', {player.mu}, {player.sigma})
        """
    )

    connection.commit()

    cursor.close()
    connection.close()


def update_player_db_rating(player: PlackettLuceRating, nid_to_players_dict: dict[str, str]) -> None:
    connection, cursor = connect_to_mysql()

    cursor.execute(
        f"""
        UPDATE PLAYER_RATING
        SET PLAYER_RATING = {float(player.mu)}, PLAYER_RATING_VOLATILITY = {float(player.sigma)}, LATEST_USERNAME = '{nid_to_players_dict[str(player.name)]}'
        WHERE APEX_ID = '{str(player.name)}';
        """
    )
    connection.commit()

    cursor.close()
    connection.close()


def player_exists_in_db(player: PlackettLuceRating) -> bool:
    connection, cursor = connect_to_mysql()

    cursor.execute(
        f"""
        SELECT EXISTS(
            SELECT 1
            FROM PLAYER_RATING 
            WHERE APEX_ID = '{player.name}'
        );
        """
    )
    exists = cursor.fetchall()

    cursor.close()
    connection.close()
    return bool(exists[0][0])


def get_team_score_list(teams_list: list[str], match) -> list[int]:
    players = match['player_results']
    team_score_dict = {}
    for idx in range(len(players)):
        team = players[idx]['teamName']
        rank = int(players[idx]['teamPlacement'])
        kills = int(players[idx]['kills'])

        if team not in team_score_dict:
            team_score_dict[team] = PLACEMENT_POINTS_DICT[rank] + kills
        else:
            team_score_dict[team] += kills

    # Make the ranking list in the correct order 
    ordered_rank_list = []
    for team in teams_list:
        ordered_rank_list.append(team_score_dict[team])

    return ordered_rank_list


def get_existing_player_rating_dict(rating_model: PlackettLuce) -> dict[str, PlackettLuceRating]:
    connection, cursor = connect_to_mysql()
    cursor.execute(
        """
        SELECT * FROM PLAYER_RATING;
        """
    )

    player_ratings = cursor.fetchall()
    cursor.close()
    connection.close()

    existing_player_dict = {}

    for player in player_ratings:
        _, _, apex_id, _, mu, sigma = player
        existing_player_dict[apex_id] = rating_model.rating(mu=float(mu), sigma=float(sigma), name=str(apex_id))

    return existing_player_dict


def connect_to_mysql() -> tuple[mysql.connector.connection, mysql.connector.cursor]: # type: ignore
    # Connect to MySQL and return connection + cursor
    connection = mysql.connector.connect(**mysql_creds)
    return connection, connection.cursor()


def make_teams_from_match(match_results_json: json, match_number: int, series_length: int = 6) -> tuple[dict[str, list[str]], dict[str, str], ]:
    matches = match_results_json['matches']
    
    match = matches[series_length - match_number]
    players = match['player_results']
    
    nid_to_players_dict = {}
    teams_to_players_dict = {}
    
    if len(players) < 45:
        return None, None, None
    
    if players[0]['teamPlacement'] == 0:
        return None, None, None
    
    for idx in range(len(players)):
        team = players[idx]['teamName']
        if team not in teams_to_players_dict:
            teams_to_players_dict[team] = []
        teams_to_players_dict[team].append(players[idx]['nidHash'])
        nid_to_players_dict[players[idx]['nidHash']] = players[idx]['playerName']
        
    return teams_to_players_dict, nid_to_players_dict, match


def get_lobby_match_history_json(lobby_name: str) -> json:
    lobby_name = lobby_name.lower()
    if lobby_name not in STATS_KEYS:
        raise ValueError(f'Invalid Lobby name please use one of the following lobby names: {list(STATS_KEYS.keys())}')
    
    return get(f'https://r5-crossplay.r5prod.stryder.respawn.com/privatematch/?token={STATS_KEYS[lobby_name]}').json()


def update_teams_rank_values(teams_to_rating_dict: dict[str, list[PlackettLuceRating]], new_ratings_list: list[list[PlackettLuceRating]])-> dict[str, list[PlackettLuceRating]]:
    for idx, team in enumerate(teams_to_rating_dict):
        teams_to_rating_dict[team] = new_ratings_list[idx]

    return teams_to_rating_dict


def get_teams_rating_str(teams_to_rating_dict: dict[str, list[PlackettLuceRating]], print_players: bool = False) -> str:
    return_string = ''
    
    if print_players:
        for team in teams_to_rating_dict:
            return_string += f'TEAM: {team}\n'
            for player in teams_to_rating_dict[team]:
                return_string += get_player_string(player)
            return_string += '\n'
    else:
        sorted_teams = []
        for team in teams_to_rating_dict:
            sorted_teams.append((team, np.mean([player.mu for player in teams_to_rating_dict[team]])))
        sorted_teams.sort(key=lambda x: x[1],)

        for team in sorted_teams:
            return_string += f'TEAM: {team[0]}\trating: {team[1]}\n'

    return return_string


def get_player_string(player: PlackettLuceRating) -> str:
    return f'\t-Name: {player.name}\n\t-Rating(mu): {player.mu}\n\t-Volatility(sigma): {player.sigma}\n\n'


def make_new_player_list(rating_model: PlackettLuce, players: list[str], existing_player_rating_dict: dict[str, PlackettLuceRating]) -> list[PlackettLuceRating]:
    team_list = []

    for player in players:
        if player in existing_player_rating_dict:
            team_list.append(existing_player_rating_dict[player])
        else:
            rating = rating_model.rating(name=player)
            team_list.append(rating)
            existing_player_rating_dict[player] = rating

    return team_list


if __name__ == '__main__':
    result = rank_lobby_matches('Ascendant', series_length=8)
    print(result)
