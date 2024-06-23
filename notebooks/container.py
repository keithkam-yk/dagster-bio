from pydantic import BaseModel
import subprocess
from typing import Any, List
import logging


logger = logging.getLogger(__name__)


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
    
    def __str__(self):
        return f"{self.image_name}:{self.image_version}"

    def get_docker_build_cmd(self, cache=True):
        if not self.dependencies:
            raise ValueError("No dependencies provided")

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

        dependencies_str = " ".join([str(dep) for dep in self.dependencies])
        docker_build_cmd.extend(
            ["--build-arg", f"CONDA_DEPENDENCIES={dependencies_str}"]
        )
        docker_build_cmd.append(".")

        return docker_build_cmd

    def build(self, cache=True):
        docker_build_cmd = self.get_docker_build_cmd(cache=cache)

        return run_subprocess(docker_build_cmd, logger)


def run_subprocess(cmd: List[str], logger: logging.Logger) -> int:
    try:
        process = subprocess.Popen(
            cmd,
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
        logger.error(f"Error running command: {e}")
        return e.returncode
