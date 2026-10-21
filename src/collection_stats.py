from pprint import pprint
from datetime import datetime
import sys

from http_utils import send_request
from providers import get_providers
from terminology_stats import calc_stats_for_one_terminology
from stats_keys import StatsKey

# region global variables
BASE_URL = "https://w3id.org/ts4nfdi/collection/"

PROPERTY = StatsKey.PROPERTY.value
CLASS = StatsKey.CLASS.value
INDIVIDUAL = StatsKey.INDIVIDUAL.value
CONCEPT = StatsKey.CONCEPT.value
TERMINOLOGY = StatsKey.TERMINOLOGY.value
# endregion

def create_selected_collection_list(collection_ids=None, include_all=False):
    collections_endpoint = "https://terminology.services.base4nfdi.de/api-gateway/collections/"
    try:
        all_collections = send_request(collections_endpoint)

        if include_all:
            return all_collections, []

        if collection_ids is None:
            return [], []

        collections = []
        collection_errors = []
        for collection_id in collection_ids:
            found = False
            for collection in all_collections:
                if collection["id"] == collection_id:
                    found = True
                    collections.append(collection)
                    break

            if not found:
                collection_errors.append({
                    "collection": {"id": collection_id},
                    "error": "Collection not found",
                })
        return collections, collection_errors

    except Exception as e:
        print(f"Unexpected answer from {collections_endpoint}: {e}.")
        raise


def calc_stats_for_collections(providers, collections):
    collection_errors = []
    collections_stats = {}
    terminologies_stats = []

    print("Calculating statistics for collections...")
    for c in collections:
        try:
            time = datetime.now().strftime("%Y-%m-%d %H:%M")

            collection_stats, this_collection_terminologies_stats = calc_stats_for_one_collection(c, providers)

            c_stats = {"created": time,
                       "count": collection_stats}

        except Exception as e:
            collection_errors.append({
                "collection": {"id": c["id"], "label": c["label"]},
                "error": str(e),
            })

            print(f"Error while processing collection '{c['id']}': {e}")
            if e.__cause__ is not None:
                print(e.__cause__)
            continue

        # collection_stats and terminologies_stats only get added if no exception occurred while processing the collection
        collections_stats[c["id"]] = c_stats
        terminologies_stats.extend(this_collection_terminologies_stats)

        # delete duplicate terminologies
        unique_terminologies = {}

        for stats in terminologies_stats:
            key = (stats["uri"], stats["source"])

            if key not in unique_terminologies:
                unique_terminologies[key] = stats

        terminologies_stats = list(unique_terminologies.values())
    return collections_stats, collection_errors, terminologies_stats


def calc_stats_for_one_collection(collection, providers):
    collection_stats = {
        TERMINOLOGY: len(collection["terminologies"]),
        PROPERTY: 0,
        CLASS: 0,
        INDIVIDUAL: 0,
        CONCEPT :  0
    }
    terminologies_stats = []

    for terminology in collection["terminologies"]:
        terminology_stats = calc_stats_for_one_terminology(terminology, providers)

        terminologies_stats.append(terminology_stats)

        collection_stats[PROPERTY] += terminology_stats[PROPERTY]
        collection_stats[CLASS] += terminology_stats[CLASS]
        collection_stats[INDIVIDUAL] += terminology_stats[INDIVIDUAL]
        collection_stats[CONCEPT] += terminology_stats[CONCEPT]

    return collection_stats, terminologies_stats

def main():
    providers = get_providers()

    if len(sys.argv) == 1:
        collections, collection_errors = create_selected_collection_list(include_all=True)
    else:
        collections, collection_errors = create_selected_collection_list(sys.argv[1:])

    collections_stats, collection_errors2, terminology_stats = calc_stats_for_collections(providers, collections)

    collection_errors = collection_errors + collection_errors2

    print("Collections stats:")
    pprint(collections_stats)

    print("Terminology stats:")
    pprint(terminology_stats)

    if len(collection_errors) > 0:
        print("For some collections no statistics could be generated.")
        pprint(collection_errors)
    else:
        print("For all collections statistics could be generated.")


if __name__ == "__main__":
    main()
