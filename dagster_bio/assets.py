import os
from pathlib import Path
from typing import Optional
from dagster import (
    AssetExecutionContext,
    AssetSelection,
    MaterializeResult,
    MetadataValue,
    asset,
    define_asset_job,
)
from dagster_docker import execute_docker_container

from dagster_bio.metadata import get_metadata
from dagster_bio.partitions import source_partition_def

DATA_VOLUME_ROOT = Path("data")


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


asset_job = define_asset_job(
    "asset_job", AssetSelection.assets("source_a"), partitions_def=source_partition_def
)
