from enum import StrEnum

class StatsKey(StrEnum):
    PROPERTY = "property_count"
    CLASS = "class_count"
    INDIVIDUAL = "named_individual_count"
    CONCEPT = "concept_count"
    TERMINOLOGY = "terminology_count"
    URI = "uri"
    SOURCE = "source"
    TIMESTAMP = "timestamp"