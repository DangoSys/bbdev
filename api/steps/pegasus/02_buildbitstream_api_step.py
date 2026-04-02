import asyncio
from utils.event_common import wait_for_result

config = {
  "type": "api",
  "name": "Pegasus Buildbitstream",
  "description": "build pegasus bitstream",
  "path": "/pegasus/buildbitstream",
  "method": "POST",
  "emits": ["pegasus.buildbitstream"],
  "flows": ["pegasus"],
}


async def handler(req, context):
  body = req.get("body") or {}
  await context.emit({"topic": "pegasus.buildbitstream", "data": body})

  while True:
    result = await wait_for_result(context)
    if result is not None:
      return result
    await asyncio.sleep(1)
