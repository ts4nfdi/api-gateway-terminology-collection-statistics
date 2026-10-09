import os
import requests
from pprint import pprint
from datetime import datetime
import psycopg
import sys

# region global variables
BASE_URL = "https://w3id.org/ts4nfdi/collection/"

# values that should be counted
PROPERTY = "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property"
CLASS = "http://www.w3.org/2002/07/owl#Class"
INDIVIDUAL = "http://www.w3.org/2002/07/owl#NamedIndividual"
CONCEPT = "http://www.w3.org/2004/02/skos/core#Concept"
# endregion

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


def create_selected_collection_list(collection_ids=None, include_all=False):
    collections_endpoint = "https://terminology.services.base4nfdi.de/api-gateway/collections/"
    try:
        all_collections = send_request(collections_endpoint)


        if include_all:
            return all_collections

        if collection_ids is None:
            return []

        collections = [c for c in all_collections if c["id"] in collection_ids]
        return collections
    except Exception as e:
        print(f"Unexpected answer from {collections_endpoint}: {e}.")
        raise


def calculate_stats_for_collections(providers, collections):
    collection_errors = []
    collections_stats = {}

    print("Calculating statistics for collections...")
    for c in collections:
        try:
            time = datetime.now().strftime("%Y-%m-%d %H:%M")

            c_stats = {"created": time,
                       "count": calculate_collection_stats(c, providers)}

        except Exception as e:
            collection_errors.append({
                "collection": {"id": c["id"], "label": c["label"]},
                "error": str(e),
            })

            print(f"Error while processing collection '{c['id']}': {e}")
            if e.__cause__ is not None:
                print(e.__cause__)
            continue

        # collection_stats only get added if not exception occurred while processing the collection
        collections_stats[c["id"]] = c_stats

    return collections_stats, collection_errors


def calculate_collection_stats(collection, providers):
    collection_stats = {
        PROPERTY: 0,
        CLASS: 0,
        INDIVIDUAL: 0,
        CONCEPT :  0
    }

    for terminology in collection["terminologies"]:
        try:
            # check for missing required values
            if terminology["label"] is None and terminology["uri"] is None:
                continue

            provider = terminology["source"]
            if not provider in providers:
                continue

            function_name = f"get_onto_stats_from_{providers[provider]['api_type']}"
            function = globals().get(function_name)
            if function is None:
                continue

            # this function adds the counts from the passed terminology to the collection_stats. How to source the
            # terminology stats is provider dependent
            function(providers[provider]["api_endpoint"], terminology, collection_stats)

        except Exception as e:
            raise RuntimeError(
                f"Error while processing terminology '{terminology.get('label')}' (URI: {terminology.get('uri')},"
                f" source: {terminology.get('source')})") from e

    return collection_stats


# region: functions to retrieve ontology stats from specific provider types
def get_onto_stats_from_ols2(api_endpoint, terminology, collection_stats):
    url = f"{api_endpoint}/ontologies/{terminology['label']}"
    data = send_request(url)

    collection_stats[CLASS] += int(data["numberOfTerms"])
    collection_stats[INDIVIDUAL] += int(data["numberOfIndividuals"])
    collection_stats[PROPERTY] += int(data["numberOfProperties"])


def get_onto_stats_from_ontoportal(api_endpoint, terminology, collection_stats):
    apikey = None
    if api_endpoint == "https://data.agroportal.eu":
        apikey = os.getenv("AGROPORTAL_API_KEY")
    elif api_endpoint == "https://data.earthportal.eu":
        apikey = os.getenv("EARTHPORTAL_API_KEY")
    elif api_endpoint == "https://data.biodivportal.gfbio.org":
        apikey = os.getenv("BIODIVPORTAL_API_KEY")
    elif api_endpoint == "https://data.ecoportal.lifewatch.eu":
        apikey = os.getenv("ECOPORTAL_API_KEY")
    elif api_endpoint == "https://data.lovportal.lirmm.fr":
        apikey = os.getenv("LOVPORTAL_API_KEY")

    if apikey is None:
        raise ValueError(f"Missing API key for provider {api_endpoint}")

    url = f"{api_endpoint}/ontologies/{terminology['label']}/metrics"
    params = {"apikey": apikey}
    data = send_request(url, params)

    collection_stats[CLASS] += int(data["classes"])
    collection_stats[INDIVIDUAL] += int(data["individuals"])
    collection_stats[PROPERTY] += int(data["properties"])


def get_onto_stats_from_skosmos(api_endpoint, terminology, collection_stats):
    url = f"{api_endpoint}/{terminology['label']}/vocabularyStatistics"
    data = send_request(url)

    collection_stats[CONCEPT] += int(data["concepts"]["count"])


def get_onto_stats_from_jskos(api_endpoint, terminology, collection_stats):
    # the number of skos:Concepts is returned in the response header under X-Total-Count
    url = f"{api_endpoint}/search"
    params = {"voc": terminology["label"],
              "limit": 1}
    data, headers = send_request(url, params, return_headers=True)

    collection_stats[CONCEPT] += int(headers["X-Total-Count"])


def get_onto_stats_from_jskos2(api_endpoint, terminology, collection_stats):
    if terminology["source"] == "coli-conc":
        # the number of skos:Concepts is returned in the response header under X-Total-Count
        url = f"{api_endpoint}/voc/concepts"
        params = {"uri": terminology["uri"]}
        data, headers = send_request(url, params, return_headers=True)


        total_count = int(headers["X-Total-Count"])
        collection_stats[CONCEPT] += total_count

    elif terminology["source"] == "iconclass":
        # The stats are retrieved by counting the number of defined blocks in notations.txt the official file for
        # the structure of iconclass. Each block responds to one skos:Concept. The blocks always end with $.
        url = "https://raw.githubusercontent.com/iconclass/data/refs/heads/main/notations.txt"

        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            content = response.content.decode("utf-8")

            blocks_count = 0
            for line in content.splitlines():
                if line.startswith("$"):
                    blocks_count += 1

            collection_stats[CONCEPT] += blocks_count


def get_onto_stats_from_gnd(api_endpoint, terminology, collection_stats):
    uri = f"{api_endpoint}/gnd/search"
    params = {"q": "*", "format": "json"}
    data = send_request(uri, params=params)

    collection_stats[CONCEPT] += int(data["totalItems"])


def get_onto_stats_from_nerc(api_endpoint, terminology, collection_stats):
    query = f"""
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT (COUNT(DISTINCT ?concept) AS ?count)
    WHERE {{
      <http://vocab.nerc.ac.uk/collection/{terminology['label']}/current/>
          skos:member ?concept .

      ?concept a skos:Concept .
    }}
    """

    data = send_request(f"{api_endpoint}/sparql/sparql",
                        params = {"query": query},
                        headers={"Accept": "application/sparql-results+json"})

    count = int(data["results"]["bindings"][0]["count"]["value"])
    collection_stats[CONCEPT] += count
# endregion


def write_to_db(collections_stats):
    if not collections_stats:
        return

    conn = None
    cursor = None

    try:
        conn = psycopg.connect(
            os.getenv("DB_URL"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD"),
        )

        cursor = conn.cursor()

        rows = []
        for collection_id, stats in collections_stats.items():
            rows.append((
                collection_id,
                stats["created"],
                stats["count"][PROPERTY],
                stats["count"][CLASS],
                stats["count"][INDIVIDUAL],
                stats["count"][CONCEPT]
                ))

        placeholders = ",".join(
            ["(%s, %s, %s, %s, %s, %s)"] * len(rows)
        )

        values = []
        for row in rows:
            for value in row:
                values.append(value)

        cursor.execute(
            f"""
            INSERT INTO "collection_statistics" (
                collection_id,
                "timestamp",
                "{PROPERTY}",
                "{CLASS}",
                "{INDIVIDUAL}",
                "{CONCEPT}"
            )
            VALUES {placeholders}
            """,
            values
        )

        conn.commit()

    except psycopg.Error as e:
        if conn is not None:
            conn.rollback()
        print(f"Database error: {e}.")
        raise

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    print("Successfully inserted collection stats into DB.")


def main():
    providers = get_providers()
    if len(sys.argv) == 1:
        collections = create_selected_collection_list(include_all=True)
    else:
        collection_ids = sys.argv[1:]
        collections = create_selected_collection_list(collection_ids)

    collections_stats, collection_errors = calculate_stats_for_collections(providers, collections)

    print("Collections stats:")
    pprint(collections_stats)
    write_to_db(collections_stats)
    if len(collection_errors) > 0:
        print("For some collections no statistics could be generated.")
        print(collection_errors)
    else:
        print("For all collections statistics could be generated.")


if __name__ == "__main__":
    main()
