import os
from pathlib import Path
from typing import Any, Optional
from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetSelection,
    DagsterEventType,
    EventRecordsFilter,
    MaterializeResult,
    MetadataValue,
    RunRequest,
    SensorEvaluationContext,
    SensorResult,
    asset,
    DynamicPartitionsDefinition,
    define_asset_job,
    sensor,
)
from dagster_docker import execute_docker_container

DATA_VOLUME_ROOT = Path("data")

source_partition_def = DynamicPartitionsDefinition(name="source")


@asset(partitions_def=source_partition_def)
def source_a(context: AssetExecutionContext):
    context.log.info(f"Loading source_a partition {context.partition_key}")

    # Load the data from the partition as str
    rel_path = Path("source_a") / context.partition_key
    path = DATA_VOLUME_ROOT / rel_path
    with open(path, "r") as f:
        contents = f.read()

    context.log.info(f"Loaded {len(contents)} bytes from {context.partition_key}")
    context.log.info(f"First 10 bytes: {contents[:10]}")

    return {
        "partition_key": context.partition_key,
        "contents": contents,
        "path": str(path),
        "rel_path": str(rel_path),
    }


@asset(partitions_def=source_partition_def)
def asset_b(context: AssetExecutionContext, source_a):
    context.log.info(f"Loading container_asset partition {context.partition_key}")

    context.log.info(source_a)

    env_vars = {
        "INPUT_FILE_PATH": f'/{source_a["path"]}',
        "OUTPUT_FILE_PATH": f"/{DATA_VOLUME_ROOT/'asset_b'/context.partition_key}",
    }
    context.log.info(f"Setting env vars: {env_vars}")

    cwd = Path(os.getcwd())
    abs_data_path = cwd / DATA_VOLUME_ROOT

    context.log.info(f"Mounting {abs_data_path} to /data in container")

    execute_docker_container(
        context=context,
        image="asset_b:latest",
        env_vars=[f"{k}={v}" for k, v in env_vars.items()],
        container_kwargs={"volumes": [f"{abs_data_path}:/data"]},
    )

    # read from output file path and log
    with open(env_vars["OUTPUT_FILE_PATH"][1:], "r") as f:  # [1:] to remove leading /
        contents = f.read()

    context.log.info(f"Output file contents: {contents}")
    return MaterializeResult(
        metadata={
            "length": len(contents),
            "preview": MetadataValue.md(contents),
            "path": env_vars["OUTPUT_FILE_PATH"],
        }
    )


@asset(partitions_def=source_partition_def)
def asset_c(context: AssetExecutionContext, asset_b):
    context.log.info(f"Asset C partition {context.partition_key}")

    asset_b_metadata = get_metadata(
        context, asset_key="asset_b", partition_key=context.partition_key
    )
    context.log.info(asset_b_metadata)
    if asset_b_metadata is not None:
        context.log.info(asset_b_metadata["path"].text)


def get_metadata(context, asset_key, partition_key) -> Optional[dict[str, Any]]:
    return context.instance.get_event_records(
        event_records_filter=EventRecordsFilter(
            event_type=DagsterEventType.ASSET_MATERIALIZATION,
            asset_key=AssetKey(asset_key),
            asset_partitions=[partition_key],
        ),
        limit=1,
    )[0].asset_materialization.metadata


asset_job = define_asset_job(
    "asset_job", AssetSelection.assets("source_a"), partitions_def=source_partition_def
)


@sensor(job=asset_job)
def source_sensor(context: SensorEvaluationContext):
    new_source_partitions = [
        source_name
        for source_name in os.listdir("data/source_a")
        if not source_partition_def.has_partition_key(
            source_name, dynamic_partitions_store=context.instance
        )
    ]

    return SensorResult(
        run_requests=[
            RunRequest(partition_key=img_filename)
            for img_filename in new_source_partitions
        ],
        dynamic_partitions_requests=[
            source_partition_def.build_add_request(new_source_partitions)
        ],
    )
