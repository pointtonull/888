# Quick Restful API

## About this Implementation

This is a coding kata. I an following a somewhat iflexible specification.
With this limits of freedom I chose to persist on DynamoDB and to implement using serverless approach (API Gateway and Lambda Functions).

It is deployed in https://z68mz9mv95.execute-api.eu-west-1.amazonaws.com/api/
It's root returns a valid Swagger object. So, to explore/test a swagger explorer can be pointed to it.

## The main functional areas are:

- Manage data about sporting events to allow users to place bets.
- Provide API to receive data from external providers and update our system
  with the latest data about events in real time.
- Provide access to support team to allow the to see the most recent data for
  each event and to query data.

## Implementation Details:

- Data:
  - Markets are unique per Sport
  - Selections are unique per Market

- Receiving data:
  - For our purposes we can assume this API will be used by a single provider,
    so no need to keep track of which provider is sending the message.
  - Receiving request from the support team:

### Retrieve match by `id`

**`GET https://{domain}/api/match/994839351740`**

```json
{
  "id": 994839351740,
  "url": "http://example.com/api/match/994839351740",
  "name": "Real Madrid vs Barcelona",
  "startTime": "2018-06-20 10:30:00",
  "sport": {
    "id": 221,
    "name": "Football"
  },
  "markets": [
    {
      "id": 385086549360973392,
      "name": "Winner",
      "selections": [
        {
          "id": 8243901714083343527,
          "name": "Real Madrid",
          "odds": 1.01
        },
        {
          "id": 5737666888266680774,
          "name": "Barcelona",
          "odds": 1.01
        }
      ]
    }
  ]
}
```

### Retrieve football matches ordered by `start_time`

**`GET https://domain/api/match?sport=football&ordering=startTime`**

```json
[
  {
    "id": 994839351740,
    "url": "http://example.com/api/match/994839351740",
    "name": "Real Madrid vs Barcelona",
    "startTime": "2018-06-20 10:30:00"
  },
  {
    "id": 994839351788,
    "url": "http://example.com/api/match/994839351788",
    "name": "Cavaliers vs Lakers",
    "startTime": "2018-01-15 22:00:00"
  }
]
```

### Retrieve matches filtered by `name`

**`GET https://domain/api/match/?name=Real%20Madrid%20vs%20Barcelona`**

```json
[
  {
    "id": 994839351740,
    "url": "http://example.com/api/match/994839351740",
    "name": "Real Madrid vs Barcelona",
    "startTime": "2018-06-20 10:30:00"
  }
]
```

## Specification for sports data sent by external providers

The external providers will send the data in a specific format.

Message types have a common structure.

### NewEvent

A complete new sporting event is being created. Once the event is created successfully the only field that can be
updated is the selection odds.

**`PUT https://domain/api/message`**

```json
{
  "id": 8661032861909884224,
  "message_type": "NewEvent",
  "event": {
    "id": 994839351740,
    "name": "Real Madrid vs Barcelona",
    "startTime": "2018-06-20 10:30:00",
    "sport": {
      "id": 221,
      "name": "Football"
    },
    "markets": [
      {
      "id": 385086549360973392,
      "name": "Winner",
      "selections": [
        {
          "id": 8243901714083343527,
          "name": "Real Madrid",
          "odds": 1.01
        },
        {
          "id": 5737666888266680774,
          "name": "Barcelona",
          "odds": 1.01
        }
      ]
      }
    ]
  }
}
```

### UpdateOdds

There is an update for the odds field (all the other fields remain unchanged).

N.B.: `POST` is used to comply with static requirements but the operation is idempotent and it should be `PUT`. As
well, this use case could be better handled accpeting a partial submition to a `PATH` endpoint.

**`POST https://domain/api/message`**

```json
{
  "id": 8661032861909884224,
  "message_type": "UpdateOdds",
  "event": {
    "id": 994839351740,
    "name": "Real Madrid vs Barcelona",
    "startTime": "2018-06-20 10:30:00",
    "sport": {
      "id": 221,
      "name": "Football"
    },
    "markets": [
      {
        "id": 385086549360973392,
        "name": "Winner",
        "selections": [
          {
            "id": 8243901714083343527,
            "name": "Real Madrid",
            "odds": 10.00
          },
          {
            "id": 5737666888266680774,
            "name": "Barcelona",
            "odds": 5.55
          }
        ]
      }
    ]
  }
}
```

### `Message` Definition

Each `message` contains the full data for that event (match).

<dl>

  <dt>id</dt>
  <dd>INTEGER the unique id for a message</dd>

  <dt>message_type</dt>
  <dd>STRING it defines the what data is going to be created/updated</dd>

  <dt>event</dt>
  <dd>the full event data</dd>

</dl>

#### `Event` definition:

The `event` represents a match being played

<dl>

  <dt>id</dt>
  <dd>INTEGER the unique id for a event</dd>

  <dt>name</dt>
  <dd>STRING name for that event</dd>

  <dt>markets</dt>
  <dd>LIST contains a list of markets (for our purposes it will be always a
  list containing a single Market)</dd>

</dl>

### `Market` definition

This contains data related to the market of that match. Markets define the kind
of bet a customer can bet on.

For our purposes we use a single market called "Winner", which means that
market is about betting on which player/teamsthe customer guess it's going to
win the match

<dl>

  <dt>id</dt>
  <dd>INTEGER the unique id for a market</dd>

  <dt>name</dt>
  <dd>STRING the name for that market</dd>

  <dt>selection</dt>
  <dd>LIST contains a list of selections</dd>

</dl>

### `Selection` definition

Selections are the players/teams playing a certain match.

For example, a football match for "Barcelona vs Real Madrid" would have 2 selections: `Real Madrid`, and `Barcelona`.

For Golf matches, you may have 3 players, so you also need to handle that.

<dl>

  <dt>id</dt>
  <dd>INTEGER the unique id for a selection</dd>

  <dt>name</dt>
  <dd>STRING the name for that selection</dd>

  <dt>odds</dt>
  <dd>FLOAT the current odds for that selection</dd>

</dl>

