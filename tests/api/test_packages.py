def test_packages_endpoint_returns_placeholder_packages(client) -> None:
    response = client.get("/api/packages")

    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 2
    assert payload["items"][0]["name"] == "Cape Town Explorer"
    assert payload["items"][0]["price_zar"] == "2499.00"
