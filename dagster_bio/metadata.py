from dagster import (
    AssetKey,
    DagsterEventType,
    EventRecordsFilter,
    MetadataValue,
    OpExecutionContext,
    PackableValue,
)


from typing import Mapping


def get_metadata(
    context: OpExecutionContext, asset_key: str, partition_key: str
) -> Mapping[str, MetadataValue[PackableValue]]:
    asset_materialization = context.instance.get_event_records(
        event_records_filter=EventRecordsFilter(
            event_type=DagsterEventType.ASSET_MATERIALIZATION,
            asset_key=AssetKey(asset_key),
            asset_partitions=[partition_key],
        ),
        limit=1,
    )[0].asset_materialization
    if not asset_materialization:
        raise ValueError(
            f"Could not find materialization for {asset_key}:{partition_key}"
        )
    return asset_materialization.metadata
