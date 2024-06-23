import os

# Get the current working directory
cwd = os.getcwd()
print(f"Current working directory: {cwd}")

# Check if the current working directory ends with "notebooks"
if cwd.endswith("notebooks"):
    # Set the cwd to the parent directory
    parent_dir = os.path.abspath(os.path.join(cwd, os.pardir))
    os.chdir(parent_dir)
    print(f"Changed working directory to parent: {parent_dir}")
else:
    print("No change in working directory needed")


from pydantic import BaseModel
import subprocess
from typing import Any, List
import logging
import select


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    return logging.getLogger(__name__)


logger = setup_logging()


def read_output(process: subprocess.Popen[Any], logger: logging.Logger) -> None:
    fd_stdout = process.stdout.fileno() if process.stdout else None
    fd_stderr = process.stderr.fileno() if process.stderr else None
    read_fds: List[int] = [fd for fd in [fd_stdout, fd_stderr] if fd is not None]

    while read_fds:
        ready, _, _ = select.select(read_fds, [], [])

        for fd in ready:
            if fd == fd_stdout and process.stdout:
                line = process.stdout.readline()
                if line:
                    logger.info(line.strip())
                else:
                    read_fds.remove(fd_stdout)
            elif fd == fd_stderr and process.stderr:
                line = process.stderr.readline()
                if line:
                    logger.error(line.strip())
                else:
                    read_fds.remove(fd_stderr)


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

    def get_docker_build_cmd(self):
        docker_build_cmd = [
            "docker",
            "build",
            "-t",
            f"{self.image_name}:{self.image_version}",
            "-f",
            "dagster_bio/Dockerfile.conda",
        ]

        if self.dependencies:
            dependencies_str = " ".join([str(dep) for dep in self.dependencies])
            dependencies_str = f'"{dependencies_str}"'
            docker_build_cmd.extend(
                ["--build-arg", f"CONDA_DEPENDENCIES={dependencies_str}"]
            )

        docker_build_cmd.append(".")

        return docker_build_cmd

    def build(self):
        docker_build_cmd = self.get_docker_build_cmd()

        try:
            process = subprocess.Popen(
                docker_build_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
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


logger.info("hello world")

flye_image = CondaImage(
    image_name="basescan-flye",
    image_version="1.0",
    dependencies=[
        Dependency(channel="bioconda", package="flye", version="2.9.3"),
        Dependency(channel="conda-forge", package="libgcc-ng", version="12"),
    ],
)

print(flye_image.get_docker_build_cmd())
print(" ".join(flye_image.get_docker_build_cmd()))

flye_image.build()

