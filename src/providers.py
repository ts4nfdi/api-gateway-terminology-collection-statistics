from http_utils import send_request


# retrieve all provider information
def get_providers() -> dict:
    providers_endpoint = "https://terminology.services.base4nfdi.de/api-gateway/config/databases"
    providers_data = send_request(providers_endpoint)
    providers = {}

    try:
        for p in providers_data:
            api_type = p["type"]
            api_endpoint = p["url"]
            providers[p["name"]] = {"api_type": api_type, "api_endpoint": api_endpoint}
    except Exception as e:
        print(f"Unexpected answer from {providers_endpoint}: {e}.")
        raise

    return providers