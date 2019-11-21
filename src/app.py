from functools import lru_cache
import os

from chalice import Chalice
from doglessdata import DataDogMetrics
import boto3

from chalicelib import controller

app = Chalice(app_name="888")

THIS = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "bet-dev")
metrics = DataDogMetrics()


def is_dev():
    lambda_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "local-dev")
    if lambda_name.endswith("-dev"):
        return True
    else:
        return False


if is_dev():
    app.debug = True

    @app.route("/env")
    @metrics.timeit
    def get_env():
        """
        Debuging endpoint.
        Describe Lambda execution environment.
        """
        return dict(os.environ)

    @app.route("/app")
    @metrics.timeit
    def get_app():
        """
        Debuging endpoint.
        Describe current app attributes.
        """
        return dir(app)

    @app.route("/app/{attr}")
    @metrics.timeit
    def get_app_attr(attr):
        """
        Debuging endpoint.
        Describe current app's {attribute}.
        """
        return str(getattr(app, attr))

    @app.route("/request", methods=["GET", "POST", "PUT"])
    @metrics.timeit
    def get_request():
        """
        Describe current request context.
        """
        request = app.current_request.to_dict()
        request["dir"] = dir(app.current_request)
        return request


@app.route("/")
@metrics.timeit
@lru_cache()
def get_root():
    """
    Describes available endpoints.
    """
    if app.current_request is None:
        context = {}
    else:
        context = app.current_request.context
    api_id = context.get("apiId")
    stage = context.get("stage")
    if api_id and stage:
        ag = boto3.client("apigateway")
        response = (
            ag.get_export(restApiId=api_id, stageName=stage, exportType="swagger",)[
                "body"
            ]
            .read()
            .decode()
        )
        return response
    else:
        endpoints = []
        for path in app.routes.values():
            for handler in path.values():
                url = "%s %s" % (handler.method, handler.uri_pattern)
                description = handler.view_function.__doc__
                doc_item = {"url": url, "description": description}
                endpoints.append(doc_item)
        response = {
            "service": "basic betting management API",
            "api": THIS,
            "endpoints": endpoints,
        }
        return response


@app.route("/match/{match_id}")
@metrics.timeit
def get_match_by_id(match_id):
    """
    Fetches details for match {id}.

    response = {
        "id": match_id,
        "url": "http://domain/api/match/994839351740",
        "name": "Real Madrid vs Barcelona",
        "startTime": "2018-06-20 10:30:00",
        "sport": {"id": 221, "name": "Football"},
        "markets": [
            {
                "id": 385086549360973400,
                "name": "Winner",
                "selections": [
                    {"id": 8243901714083343000, "name": "Real Madrid", "odds": 1.01},
                    {"id": 5737666888266680000, "name": "Barcelona", "odds": 1.01},
                ],
            }
        ],
    }
    """
    return controller.get_match_by_id(match_id)


@app.route("/matches")
@metrics.timeit
def get_matches():
    """
    Searchs matches in {sport}.
    Options:
        ordening=[startTime]

    e.g.:
        `GET https://domain/api/matches?sport=football`
        `GET https://domain/api/matches?sport=chess`

    [
      {
        "id": {id},
        "url": "http://example.com/api/match/{id}",
        "name": "Real Madrid vs Barcelona",
        "startTime": "2018-06-20 10:30:00"
      },
      {
        "id": {id},
        "url": "http://example.com/api/match/{id}",
        "name": "Cavaliers vs Lakers",
        "startTime": "2018-01-15 22:00:00"
      }
    ]

    `GET https://domain/api/matches?name=Real%20Madrid%20vs%20Barcelona`

    [
      {
        "id": {id},
        "url": "http://example.com/api/match/994839351740",
        "name": "Real Madrid vs Barcelona",
        "startTime": "2018-06-20 10:30:00"
      }
    ]
    """
    query_params = app.current_request.query_params
    response = controller.get_matches(query_params)
    return response


@app.route("/message", methods=["PUT"], content_types=["application/json"])
@metrics.timeit
def put_message():
    """
    `PUT https://domain/api/message`
    """
    data = app.current_request.raw_body
    result = controller.put_message(data)
    return result


@app.route("/message", methods=["POST"], content_types=["application/json"])
@metrics.timeit
def post_message():
    """
    `POST https://domain/api/message`

    {
      "id": {id},
      "message_type": "NewEvent",
      "event": {
        "id": {id},
        "name": {name},
        "startTime": {date},
        "sport": {
          "id": {id},
          "name": {sport}
        },
        "markets": [
          {
            "id": {id},
            "name": "Winner",
            "selections": [
              {
                "id": {id},
                "name": "Real Madrid",
                "odds": 1.01
              },
              {
                "id": {id},
                "name": "Barcelona",
                "odds": 1.01
              }
            ]
          }
        ]
      }
    }
    """
    payload = app.current_request.raw_body
    result = controller.post_message(payload)
    return result
