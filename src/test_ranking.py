import json

from openskill.models.weng_lin.plackett_luce import PlackettLuce, PlackettLuceRating
from settings.project_secrets import STATS_KEYS
from requests import get


# teams_and_players_dict = {
#     'Scrub Squad': ['fizzy000', '#FreeMelee', 'Blu'],
#     'Vesa goats and Sly': ['booch', 'amy', 'slytitan'],
#     'Goat team': ['ItzTimmy', 'Wxltzy', 'Lou'],
#     'falcons': ['hal', 'darkZero', 'who knows'],
#     'apex legends': ['gibby', 'octane', 'bangalore']
# }


def main():
    
    match_results_json = get_lobby_match_history_json('ascendant')
    print(f'match_results: {match_results_json}')

    teams_and_players_dict = make_teams_from_match(match_results_json, 6, 6)

    rating_model = PlackettLuce()
    teams_to_rating_dict = {}
    for team in teams_and_players_dict:
        teams_to_rating_dict[team] = make_new_player_list(rating_model=rating_model, players=teams_and_players_dict[team])

    print_teams_rating(teams_to_rating_dict)

    new_ratings_list = rating_model.rate(
        teams=list(teams_to_rating_dict.values()),
        ranks=[1, 5, 4, 2, 3],
        # scores=[81, 21, 27, 55, 42]
    )
    teams_to_rating_dict = update_teams_rank_values(teams_to_rating_dict=teams_to_rating_dict, new_ratings_list=new_ratings_list)
    print_teams_rating(teams_to_rating_dict)

    print(f'done')


def make_teams_from_match(match_results_json: json, match_number: int, series_length: int = 6) -> dict[str, list[str]]:
    matches = match_results_json['matches']
    match = matches[series_length - match_number]
    players = match['player_results']

    teams_to_players_dict = {}
    for idx in range(len(players)):
        team = players[idx]['teamName']
        if team not in teams_to_players_dict:
            teams_to_players_dict[team] = []
        teams_to_players_dict[team].append(players[idx]['playerName'])
        
    return teams_to_players_dict


def get_lobby_match_history_json(lobby_name: str) -> json:
    if lobby_name not in STATS_KEYS:
        raise ValueError(f'Invalid Lobby name please use one of the following lobby names: {list(STATS_KEYS.keys())}')
    
    return get(f'https://r5-crossplay.r5prod.stryder.respawn.com/privatematch/?token={STATS_KEYS[lobby_name]}').json()


def update_teams_rank_values(teams_to_rating_dict: dict[str, list[PlackettLuceRating]], new_ratings_list: list[list[PlackettLuceRating]])-> dict[str, list[PlackettLuceRating]]:
    for idx, team in enumerate(teams_to_rating_dict):
        teams_to_rating_dict[team] = new_ratings_list[idx]

    return teams_to_rating_dict


def print_teams_rating(teams_to_rating_dict: dict[str, list[PlackettLuceRating]]) -> None:
    for team in teams_to_rating_dict:
        print(f'\nteam:')
        for player in teams_to_rating_dict[team]:
            print(player)


def make_new_player_list(rating_model: PlackettLuce, players: list[str]) -> list[PlackettLuceRating]:
    team_list = []
    for player in players:
        team_list.append(rating_model.rating(name=player))
    return team_list


if __name__ == '__main__':
    main()
