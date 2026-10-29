"""Check create, read, update, and delete against a temporary verification API."""

import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request(base_url, method, path, payload=None):
    """Send JSON to the local verification API; return status and decoded body."""
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(
        base_url + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urlopen(req, timeout=15) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def verify(base_url):
    """Exercise one temporary house record; raise if any CRUD result is wrong."""
    house = dict(bedrooms=3, bathrooms=2.0, sqft_living=1500, grade=7, zipcode="98178")
    status, created = request(base_url, "POST", "/houses", house)
    assert status == 201 and created == house | {"id": created["id"]}
    path = f"/houses/{created['id']}"
    assert request(base_url, "GET", path) == (200, created)
    assert created in request(base_url, "GET", "/houses")[1]
    updated = house | {"bedrooms": 4}
    assert request(base_url, "PUT", path, updated) == (
        200,
        updated | {"id": created["id"]},
    )
    assert request(base_url, "GET", path)[1]["bedrooms"] == 4
    assert request(base_url, "DELETE", path) == (204, None)
    try:
        request(base_url, "GET", path)
    except HTTPError as error:
        assert error.code == 404
    else:
        raise AssertionError("Deleted house is still readable")
    print("Published image CRUD verification passed.")


if __name__ == "__main__":
    verify(sys.argv[1])
