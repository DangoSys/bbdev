import os
import sys

from motia import FlowContext, queue

# Add the utils directory to the Python path
utils_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)

from utils.path import get_buckyball_path
from utils.stream_run import stream_run_logger
from utils.event_common import check_result

config = {
    "name": "running sardine",
    "description": "running sardine",
    "flows": ["sardine"],
    "triggers": [queue("sardine.run")],
    "enqueues": [],
}


async def handler(input_data: dict, ctx: FlowContext) -> None:
    bbdir = get_buckyball_path()

    sardine_dir = f"{bbdir}/bb-tests/sardine"

    command = f"python3 run_tests.py -m \"({input_data.get('workload', '')})\""
    ctx.logger.info(
        "Executing sardine command", {"command": command, "cwd": sardine_dir}
    )
    result = stream_run_logger(
        cmd=command,
        logger=ctx.logger,
        cwd=sardine_dir,
        executable="bash",
        stdout_prefix="sardine run",
        stderr_prefix="sardine run",
    )

    # ==================================================================================
    # Return execution result
    # ==================================================================================
    success_result, failure_result = await check_result(
        ctx, result.returncode, continue_run=False
    )

    # ==================================================================================
    #  finish workflow
    # ==================================================================================
    return
