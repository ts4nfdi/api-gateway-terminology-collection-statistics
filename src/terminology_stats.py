from datetime import datetime
import requests
from pprint import pprint
import os

from http_utils import send_request
from providers import get_providers
from stats_keys import StatsKey

# region global variables
PROPERTY = StatsKey.PROPERTY.value
CLASS = StatsKey.CLASS.value
INDIVIDUAL = StatsKey.INDIVIDUAL.value
CONCEPT = StatsKey.CONCEPT.value
URI = StatsKey.URI.value
SOURCE = StatsKey.SOURCE.value
TIMESTAMP = StatsKey.TIMESTAMP.value

TERMINOLOGY_STATS_TEMPLATE = {URI: None,
                              SOURCE: None,
                              TIMESTAMP: None,
                              PROPERTY: 0,
                              CLASS: 0,
                              INDIVIDUAL: 0,
                              CONCEPT: 0}
# endregion


def calc_stats_for_one_terminology(terminology, providers) -> dict:
    try:
        # check for missing required values
        if terminology["label"] is None and terminology["uri"] is None:
            raise ValueError("terminology must contain label or uri")

        provider = terminology["source"]
        if not provider in providers:
            raise ValueError("provider not valid")

        function_name = f"get_onto_stats_from_{providers[provider]['api_type']}"
        function = globals().get(function_name)
        if function is None:
            raise InternalServerError(f"function {function_name} not found")

        # How to source the terminology stats is provider dependent
        terminology_stats = TERMINOLOGY_STATS_TEMPLATE.copy()

        # How to source the terminology stats is provider dependent. The function adds the counts to terminology_stats
        function(providers[provider]["api_endpoint"], terminology, terminology_stats)

        # add uri to statistics (if not available take label)
        if terminology["uri"] is not None:
            terminology_stats[URI] = terminology["uri"]
        else:
            terminology_stats[URI] = terminology["label"]

        # add source to statistics
        terminology_stats[SOURCE] = terminology["source"]

        # add timestamp
        terminology_stats[TIMESTAMP] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return terminology_stats

    except Exception as e:
        raise RuntimeError(
            f"Error while processing terminology '{terminology.get('label')}' (URI: {terminology.get('uri')},"
            f" source: {terminology.get('source')})") from e


def get_onto_stats_from_ols2(api_endpoint, terminology, terminology_stats):
    url = f"{api_endpoint}/ontologies/{terminology['label']}"
    data = send_request(url)

    terminology_stats[CLASS] += int(data["numberOfTerms"])
    terminology_stats[INDIVIDUAL] += int(data["numberOfIndividuals"])
    terminology_stats[PROPERTY] += int(data["numberOfProperties"])


def get_onto_stats_from_ontoportal(api_endpoint, terminology, terminology_stats):
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

    terminology_stats[CLASS] += int(data["classes"])
    terminology_stats[INDIVIDUAL] += int(data["individuals"])
    terminology_stats[PROPERTY] += int(data["properties"])


def get_onto_stats_from_skosmos(api_endpoint, terminology, terminology_stats):
    url = f"{api_endpoint}/{terminology['label']}/vocabularyStatistics"
    data = send_request(url)

    terminology_stats[CONCEPT] += int(data["concepts"]["count"])


def get_onto_stats_from_jskos(api_endpoint, terminology, terminology_stats):
    # the number of skos:Concepts is returned in the response header under X-Total-Count
    url = f"{api_endpoint}/search"
    params = {"voc": terminology["label"],
              "limit": 1}
    data, headers = send_request(url, params, return_headers=True)

    terminology_stats[CONCEPT] += int(headers["X-Total-Count"])


def get_onto_stats_from_jskos2(api_endpoint, terminology, terminology_stats):
    if terminology["source"] == "coli-conc":
        # the number of skos:Concepts is returned in the response header under X-Total-Count
        url = f"{api_endpoint}/voc/concepts"
        params = {"uri": terminology["uri"]}
        data, headers = send_request(url, params, return_headers=True)


        total_count = int(headers["X-Total-Count"])
        terminology_stats[CONCEPT] += total_count

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

            terminology_stats[CONCEPT] += blocks_count


def get_onto_stats_from_gnd(api_endpoint, terminology, terminology_stats):
    uri = f"{api_endpoint}/gnd/search"
    params = {"q": "*", "format": "json"}
    data = send_request(uri, params=params)

    terminology_stats[CONCEPT] += int(data["totalItems"])


def get_onto_stats_from_nerc(api_endpoint, terminology, terminology_stats):
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
    terminology_stats[CONCEPT] += count


def main():
    providers = get_providers()

    # tests
    iconclass = {'uri': None, 'label': 'ICONCLASS', 'source': 'iconclass', 'type': None}
    p07 = {"uri": "http://vocab.nerc.ac.uk/artefacts/P07", "label": "P07", "source": "nerc", "type": None}
    msio = {"uri": "msio", "label": "msio", "source": "tib", "type": None}

    pprint(calc_stats_for_one_terminology(iconclass, providers))
    pprint(calc_stats_for_one_terminology(p07, providers))
    pprint(calc_stats_for_one_terminology(msio, providers))


if __name__ == "__main__":
    main()
