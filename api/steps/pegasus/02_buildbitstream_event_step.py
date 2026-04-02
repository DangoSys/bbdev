import os
import sys

utils_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if utils_path not in sys.path:
  sys.path.insert(0, utils_path)

from utils.path import get_buckyball_path
from utils.stream_run import stream_run_logger
from utils.event_common import check_result

config = {
  "type": "event",
  "name": "Pegasus Buildbitstream",
  "description": "build pegasus bitstream",
  "subscribes": ["pegasus.buildbitstream"],
  "emits": [],
  "flows": ["pegasus"],
}


async def handler(data, context):
  bbdir = get_buckyball_path()
  generated_dir = data.get("generated_dir", f"{bbdir}/pegasus/vivado/generated")
  output_dir = data.get("output_dir", f"{bbdir}/pegasus/vivado/build")
  top_module = data.get("top", "PegasusHarness")

  context.logger.info(f"[pegasus] Generated dir: {generated_dir}")
  context.logger.info(f"[pegasus] Output dir: {output_dir}")

  os.makedirs(output_dir, exist_ok=True)

  if not os.path.isdir(generated_dir):
    context.logger.error(f"[pegasus] generated dir not found: {generated_dir}")
    success_result, failure_result = await check_result(
      context,
      1,
      continue_run=False,
      extra_fields={"task": "buildbitstream", "error": "missing generated_dir"},
    )
    return failure_result

  has_rtl = any(name.endswith(".sv") or name.endswith(".v") for name in os.listdir(generated_dir))
  if not has_rtl:
    context.logger.error(f"[pegasus] no verilog files found in: {generated_dir}")
    success_result, failure_result = await check_result(
      context,
      1,
      continue_run=False,
      extra_fields={"task": "buildbitstream", "error": "empty generated_dir"},
    )
    return failure_result

  bit_cmd = (
    f"bash {bbdir}/pegasus/vivado/build-bitstream.sh "
    f"--source_dir {generated_dir} "
    f"--output_dir {output_dir} "
    f"--top {top_module}"
  )
  result = stream_run_logger(
    cmd=bit_cmd,
    logger=context.logger,
    cwd=bbdir,
    stdout_prefix="pegasus bitstream",
    stderr_prefix="pegasus bitstream",
  )

  success_result, failure_result = await check_result(
    context,
    result.returncode,
    continue_run=False,
    extra_fields={
      "task": "buildbitstream",
      "output_dir": output_dir,
      "bitstream": f"{output_dir}/{top_module}.bit",
    },
  )
  return
