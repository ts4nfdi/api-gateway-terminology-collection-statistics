import os
import psycopg

from stats_keys import StatsKey

PROPERTY = StatsKey.PROPERTY.value
CLASS = StatsKey.CLASS.value
INDIVIDUAL = StatsKey.INDIVIDUAL.value
CONCEPT = StatsKey.CONCEPT.value
TERMINOLOGY = StatsKey.TERMINOLOGY.value
URI = StatsKey.URI.value
SOURCE = StatsKey.SOURCE.value
TIMESTAMP = StatsKey.TIMESTAMP.value

def get_connection():
    return psycopg.connect(
        os.getenv("DB_URL"),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
    )


def insert_collection_stats(collections_stats, connection):
    if not collections_stats:
        return

    rows = []
    for collection_id, stats in collections_stats.items():
        rows.append(
            (
                collection_id,
                stats["created"],
                stats["count"][TERMINOLOGY],
                stats["count"][PROPERTY],
                stats["count"][CLASS],
                stats["count"][INDIVIDUAL],
                stats["count"][CONCEPT],
            )
        )

    placeholders = ",".join(["(%s, %s, %s, %s, %s, %s, %s)"] * len(rows))

    values = []
    for row in rows:
        for value in row:
            values.append(value)

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO "collection_statistics" (
                collection_id,
                "timestamp",
                {TERMINOLOGY},
                {PROPERTY},
                {CLASS},
                {INDIVIDUAL},
                {CONCEPT}
            )
            VALUES {placeholders}
            """,
            values
        )


def insert_terminology_stats(terminologies_stats, connection):
    if not terminologies_stats:
        return

    rows = []
    for terminology_stats in terminologies_stats:
        rows.append(
            (
                terminology_stats[URI],
                terminology_stats[SOURCE],
                terminology_stats[TIMESTAMP],
                terminology_stats[PROPERTY],
                terminology_stats[CLASS],
                terminology_stats[INDIVIDUAL],
                terminology_stats[CONCEPT],
            )
        )

    placeholders = ",".join(["(%s, %s, %s, %s, %s, %s, %s)"] * len(rows))

    values = []
    for row in rows:
        for value in row:
            values.append(value)

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO "terminology_statistics" (
                {URI},
                {SOURCE},
                {TIMESTAMP},
                {PROPERTY},
                {CLASS},
                {INDIVIDUAL},
                {CONCEPT}
            )
            VALUES {placeholders}
            """,
            values
        )
