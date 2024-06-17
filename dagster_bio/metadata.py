from dagster import AssetKey, DagsterEventType, EventRecordsFilter


from typing import Any, Optional


def get_metadata(context, asset_key, partition_key) -> Optional[dict[str, Any]]:
    return context.instance.get_event_records(
        event_records_filter=EventRecordsFilter(
            event_type=DagsterEventType.ASSET_MATERIALIZATION,
            asset_key=AssetKey(asset_key),
            asset_partitions=[partition_key],
        ),
        limit=1,
    )[0].asset_materialization.metadata
