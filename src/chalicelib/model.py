"""
Database interface
"""

import os
from decimal import Decimal as D
from datetime import datetime

from Levenshtein import distance
from boto3.dynamodb.conditions import Key, Attr
from chalice import NotFoundError, UnprocessableEntityError
from functools import reduce
import boto3
from botocore.exceptions import ClientError
import jsonschema

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
BET_TABLE_MAP = {
    "AttributeDefinitions": [
        {"AttributeName": "id", "AttributeType": "N"},
        {"AttributeName": "startTime", "AttributeType": "N"},
        {"AttributeName": "_sport", "AttributeType": "S"},
    ],
    "KeySchema": [
        {"AttributeName": "id", "KeyType": "HASH"},
    ],
    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "sport_startTime",
            "KeySchema": [
                {"AttributeName": "_sport", "KeyType": "HASH"},
                {"AttributeName": "startTime", "KeyType": "RANGE"},
            ],
            "Projection": {"NonKeyAttributes": ["name"], "ProjectionType": "INCLUDE"},
            "ProvisionedThroughput": {"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        }
    ],
}


SCHEMA_MESSAGE = {
    "type": "object",
    "definitions": {
        "selection": {
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "odds": {"type": "number"},
            },
        },
        "market": {
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "selections": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/selection"},
                },
            },
            "required": ["id", "name"],
        },
    },
    "properties": {
        "id": {"type": "integer"},
        "message_type": {"type": "string"},
        "event": {
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "startTime": {"type": "string", "format": "date-time"},
                "sport": {
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                    "required": ["id", "name"],
                },
                "markets": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/market"},
                },
            }
        },
    },
}


def clean_dict(insecure_dict):
    """
    Deletes private items in dict.
    """
    clean_dict = {key: value
                  for key, value in insecure_dict.items()
                  if not key.startswith("_")}
    if "startTime" in clean_dict:
        start_time = datetime.fromtimestamp(clean_dict["startTime"])
        clean_dict["startTime"] = start_time.strftime(DATE_FORMAT)
    return clean_dict


class Bets:
    """
    Database interface for Matches and meta-info.
    """

    table = None

    def __init__(self, table_name=None):
        """Initialize tables"""
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")

    def init_table(self):
        """
        Looks for matching export.
        Creates table interface resource instance.
        """
        if self.table_name is None:
            this = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "bet-dev")
            stage = this.split("-")[-1]
            self.table_name = "betting-table-%s" % stage

        if not self.table:
            try:
                table = self.dynamodb.create_table(TableName=self.table_name, **BET_TABLE_MAP)
                table.meta.client.get_waiter('table_exists').wait(TableName='users')
            except Exception as error:
                if error.__class__.__name__ != "ResourceInUseException":
                    raise RuntimeError(
                        "Create table if not exists request "
                        f"failed: Exception of type {type(error)} "
                        f"occurred: {error}"
                    )
            self.table = self.dynamodb.Table(self.table_name)

    def get_match(self, match_id):
        self.init_table()
        response = self.table.get_item(Key={"id": match_id})
        match = response.get("Item")
        if not match:
            raise NotFoundError(f"{match_id} not found")
        match = clean_dict(match)
        return match

    def get_matches_by_sport(self, sport):
        self.init_table()
        key_sport = Key("_sport")
        response = self.table.query(
            IndexName="sport_startTime", KeyConditionExpression=key_sport.eq(sport)
        )
        items = response["Items"]
        items = [clean_dict(item) for item in items]
        return items

    def get_matches_by_name(self, names):
        self.init_table()
        attr_name = Attr("name")
        names = " ".join(names)
        words = [word for word in names.split() if 3 <= len(word)]
        filters = [attr_name.contains(word) for word in words]

        if not filters:
            return []

        filter_expression = reduce(lambda left, right: left | right, filters)

        response = self.table.scan(FilterExpression=filter_expression)
        matches = [clean_dict(item) for item in response["Items"]]

        def relevance(match):
            name = match["name"]
            mean = sum(distance(word, name) for word in words) / len(words)
            return mean / len(match)

        matches.sort(key=relevance, reverse=True)
        return matches

    def put_message(self, message):
        self.init_table()
        try:
            jsonschema.validate(message, SCHEMA_MESSAGE)
        except jsonschema.ValidationError as error:
            message = f"{error}\n\nExpected schema:\n{SCHEMA_MESSAGE}"
            raise UnprocessableEntityError(message)

        match = message["event"]
        match["_sport"] = match["sport"]["name"]  # trick to allow nested indexing

        new_item = "attribute_not_exists(id)"
        try:
            response = self.table.put_item(Item=match, ConditionExpression=new_item)
        except ClientError as error:
            response = error.response
            uid = match["id"]
            if response["Error"]["Code"] == "ConditionalCheckFailedException":
                response = {"reason": f"The match with id `{uid}` already exists."}
        return response

    def post_message(self, payload):
        self.init_table()
        try:
            jsonschema.validate(payload, SCHEMA_MESSAGE)
        except jsonschema.ValidationError as error:
            message = "%s\n\nExpected schema:\n%s" % (error, SCHEMA_MESSAGE)
            raise UnprocessableEntityError(message)

        event = payload["event"]
        start_time = event["startTime"]
        start_time = datetime.strptime(start_time, DATE_FORMAT)
        event["startTime"] = D(start_time.timestamp())
        response = self.table.put_item(Item=event)
        return response
