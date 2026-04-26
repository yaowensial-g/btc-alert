import requests


def get_btc_price(vs_currency="usd"):
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": vs_currency,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    return float(data["bitcoin"][vs_currency])


if __name__ == "__main__":
    price = get_btc_price()
    print(f"Current BTC price: {price} USD")
