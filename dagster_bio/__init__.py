from dagster import Definitions, load_assets_from_modules


from . import assets, sensors

all_assets = load_assets_from_modules([assets])


defs = Definitions(
    assets=all_assets,
    sensors=[sensors.source_sensor],
    jobs=[assets.asset_job],
)
