from pydantic import BaseModel
import subprocess
from typing import Any, List
import logging


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    return logging.getLogger(__name__)


logger = setup_logging()


def read_output(process: subprocess.Popen[Any], logger: logging.Logger) -> None:
    for line in process.stdout:
        logger.info(line.strip())


class Dependency(BaseModel):
    channel: str
    package: str
    version: str

    def __str__(self):
        return f"{self.channel}::{self.package}={self.version}"


class CondaImage(BaseModel):
    image_name: str
    image_version: str
    dependencies: List[Dependency]

    def get_docker_build_cmd(self, cache=True):
        docker_build_cmd = [
            "docker",
            "build",
            "--progress=plain",
            "-t",
            f"{self.image_name}:{self.image_version}",
            "-f",
            "dagster_bio/Dockerfile.conda",
        ]
        
        if not cache:
            docker_build_cmd.append("--no-cache")

        if self.dependencies:
            dependencies_str = " ".join([str(dep) for dep in self.dependencies])
            docker_build_cmd.extend(
                ["--build-arg", f"CONDA_DEPENDENCIES={dependencies_str}"]
            )

        docker_build_cmd.append(".")

        return docker_build_cmd

    def build(self, cache=True):
        docker_build_cmd = self.get_docker_build_cmd(cache=cache)

        try:
            process = subprocess.Popen(
                docker_build_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            read_output(process, logger)

            return_code = process.wait()
            return return_code

        except subprocess.CalledProcessError as e:
            logger.error(f"Error building Docker image: {e}")
            return e.returncode
