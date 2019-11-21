# flake8: noqa: B101

"""
App interface tests cases
"""

import json
import urllib
from decimal import Decimal
from http import HTTPStatus

import pytest
from chalice.local import ForbiddenError
from moto import mock_dynamodb2

from chalicelib import controller
import app


def deep_diff(left, right, keys=[]):
    """
    Allows for recursive approx comparassions. This is needed for acurate assesment of relevant differences in
    complex JSON objects.
    """
    if isinstance(left, dict):
        for key in left.keys():
            diff = deep_diff(left[key], right[key], keys + [key])
            if diff:
                return diff
    elif isinstance(left, list):
        for key, (left_value, right_value) in enumerate(zip(left, right)):
            diff = deep_diff(left_value, right_value, keys + [key])
            if diff:
                return diff
    else:
        try:
            if pytest.approx(left) != float(right):
                return f"sub-key `{keys}` differs: {left} != {right}"
        except TypeError:
            if left != right:
                return f"sub-key `{keys}` differs: {left} != {right}"


class TestEndpoints:

    def test__get_root__returns_valid_dict(self, client):
        response = client.get("/")
        assert response.status_code == HTTPStatus.OK
        result = response.json
        assert isinstance(result, dict)
        assert "service" in result
        assert "endpoints" in result

        endpoints = [ep["url"] for ep in result["endpoints"]]
        expected_endpoints = [
            "GET /",
            "GET /match/{match_id}",
            "GET /matches",
            "POST /message",
            "POST /request",
            "PUT /message",
            "PUT /request",
        ]
        for endpoint in expected_endpoints:
            assert endpoint in endpoints

    def test__get_app__accepts_no_argument(self, client):
        response = client.get("/app")
        assert response.status_code == HTTPStatus.OK

    def test__get_app_attr__signature(self, client):
        some_attrs = ["api", "app_name", "debug", "route", "routes"]
        for attr in some_attrs:
            response = client.get(f"/app/{attr}")
            assert response.status_code == HTTPStatus.OK

    def test__get_env(self, client):
        response = client.get("/env")
        assert response.status_code == HTTPStatus.OK

    @mock_dynamodb2
    def test__get_match_by_id__signature(self, client):
        with pytest.raises(ForbiddenError):
            response = client.get(f"/match")

        match_id = "NotAnInteger"
        response = client.get(f"/match/{match_id}")
        assert response.status_code == HTTPStatus.BAD_REQUEST

        match_id = 0
        response = client.get(f"/match/{match_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @mock_dynamodb2
    def test__get_match_by_id__examples(self, client, message):

        match_id = 1
        message["event"]["id"] = match_id
        given = message["event"]
        message_json = json.dumps(message)
        response = controller.post_message(message_json)
        stored = controller.get_match_by_id(match_id)
        assert not deep_diff(given, stored)

        match_id = 2
        response = client.get(f"/match/{match_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @mock_dynamodb2
    def test__get_matches_by_name(self, app, client):
        url = "/matches?name=Barcelona"
        query_string = url.split("?")[-1]
        query_dict = urllib.parse.parse_qs(query_string)
        matches = controller.get_matches(query_dict)

        response = client.get("/matches?name=Barcelona")
        assert response.status_code == HTTPStatus.OK

    @mock_dynamodb2
    def test__get_match__by_sport(self, client, message, match):
        response = client.get("/matches?sport=football")
        assert response.status_code == HTTPStatus.OK

        match_id = 1
        message["event"]["id"] = match_id
        response = client.post("/message", body=json.dumps(message))
        assert response.status_code == HTTPStatus.OK

        response = client.get("/matches?sport=football")
        assert response.status_code == HTTPStatus.OK

        response = client.get("/matches?sport=chess")
        assert response.status_code == HTTPStatus.OK
        response = client.get("/matches?sport=football&ordering=startTime")
        assert response.status_code == HTTPStatus.OK


class TestHelpers:
    def test__is_dev(self):
        assert app.is_dev()
