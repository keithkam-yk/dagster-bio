import os
from pathlib import Path
from dagster import (
    AssetExecutionContext,
    AssetSelection,
    RunRequest,
    SensorEvaluationContext,
    SensorResult,
    asset,
    DynamicPartitionsDefinition,
    define_asset_job,
    sensor,
)
from dagster_docker import execute_docker_container

DATA_VOLUME_ROOT = "data/"

source_partition_def = DynamicPartitionsDefinition(name="source")


@asset(partitions_def=source_partition_def)
def source_a(context: AssetExecutionContext):
    context.log.info(f"Loading source_a partition {context.partition_key}")

    # Load the data from the partition as str
    rel_path = f"source_a/{context.partition_key}"
    path = DATA_VOLUME_ROOT + rel_path
    with open(path, "r") as f:
        contents = f.read()

    context.log.info(f"Loaded {len(contents)} bytes from {context.partition_key}")
    context.log.info(f"First 10 bytes: {contents[:10]}")

    return {
        "partition_key": context.partition_key,
        "contents": contents,
        "path": path,
        "rel_path": rel_path,
    }


@asset(partitions_def=source_partition_def)
def asset_b(context: AssetExecutionContext, source_a):
    context.log.info(f"Loading container_asset partition {context.partition_key}")

    context.log.info(source_a)

    input_file_env_var = "INPUT_FILE_PATH=/" + source_a["path"]
    output_file_env_var = (
        "OUTPUT_FILE_PATH=/" + DATA_VOLUME_ROOT + f"asset_b/{context.partition_key}"
    )
    context.log.info(f"Setting env vars: {input_file_env_var}, {output_file_env_var}")

    cwd = Path(os.getcwd())
    abs_data_path = cwd / DATA_VOLUME_ROOT

    context.log.info(f"Mounting {abs_data_path} to /data in container")

    execute_docker_container(
        context=context,
        image="asset_b:latest",
        env_vars=[input_file_env_var, output_file_env_var],
        container_kwargs={"volumes": [f"{abs_data_path}:/data"]},
    )


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
