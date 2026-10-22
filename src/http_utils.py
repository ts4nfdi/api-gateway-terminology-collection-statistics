import requests

# template to send requests
def send_request(url, params=None, headers=None, return_headers=False):
    response = requests.get(
        url,
        params=params or {},
        headers=headers or {},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    if return_headers:
        return data, response.headers

    return data