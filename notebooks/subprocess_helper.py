import subprocess
from typing import Any, List
import logging


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


def read_output(process: subprocess.Popen[Any], logger: logging.Logger) -> None:
    if not process.stdout:
        return
    for line in process.stdout:
        logger.info(line.strip())
