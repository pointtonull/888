from decimal import Decimal
import json

from chalice import BadRequestError

from . import model

BETS = model.Bets()


def get_match_by_id(match_id):
    try:
        match_id = int(match_id)
    except ValueError:
        raise BadRequestError(f"`match_id` must be an integer, got `{match_id}`")

    match = BETS.get_match(match_id)
    return match


def post_message(data: str):
    """helper for debugging"""
    payload = json.loads(data, parse_float=Decimal)
    result = BETS.post_message(payload)
    return result


def put_message(data):
    """
    `PUT https://domain/api/message`
    """
    payload = json.loads(data, parse_float=Decimal)
    result = BETS.put_message(payload)
    return result


def get_matches(query_params: dict):
    name = query_params.get("name")
    sport = query_params.get("sport")
    if name and sport:
        raise NotImplementedError(
            f"{query_params}, only one of ['name', 'sport'] can be specified"
        )
    elif name:
        matches = BETS.get_matches_by_name(name)
    elif sport:
        matches = BETS.get_matches_by_sport(sport)
    else:
        matches = BETS.get_matches_by_name("")
    return matches
