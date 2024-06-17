from dagster import DynamicPartitionsDefinition


source_partition_def = DynamicPartitionsDefinition(name="source")
