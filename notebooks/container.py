from pydantic import BaseModel
from typing import List, Optional
import logging
from subprocess_helper import run_subprocess


logger = logging.getLogger(__name__)


class Dependency(BaseModel):
    channel: str
    package: str
    version: str

    def __str__(self):
        return f"{self.channel}::{self.package}={self.version}"


class CondaImage(BaseModel):
    registry: Optional[str] = None
    repository: str
    tag: str
    dependencies: List[Dependency]

    def __str__(self):
        if self.registry:
            return f"{self.registry}/{self.repository}:{self.tag}"
        return f"{self.repository}:{self.tag}"

    def get_docker_build_cmd(self, cache=True):
        if not self.dependencies:
            raise ValueError("No dependencies provided")

        docker_build_cmd = [
            "docker",
            "build",
            "--progress=plain",
            "-t",
            f"{self.repository}:{self.tag}",
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

    # TODO: Add a method to push the image to a registry
