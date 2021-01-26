MAX_BIGQUERY_OPERATIONS_PER_DAY = 1000
"""The maximum number of BigQuery operations permitted per table per day."""

PERMITTED_OPERATIONS_PER_DAY = MAX_BIGQUERY_OPERATIONS_PER_DAY * 0.5
"""How much of the BigQuery operations allowance to actually use, to leave headroom for other things."""
