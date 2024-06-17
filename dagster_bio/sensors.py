from dagster_bio.assets import asset_job
from dagster_bio.partitions import source_partition_def


from dagster import RunRequest, SensorEvaluationContext, SensorResult, sensor


import os


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
