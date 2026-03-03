import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result

config = {
    "name": "Firesim Buildbitstream",
    "description": "build bitstream",
    "flows": ["firesim"],
    "triggers": [http("POST", "/firesim/buildbitstream")],
    "enqueues": ["firesim.buildbitstream"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    body = request.body or {}
    await ctx.enqueue({"topic": "firesim.buildbitstream", "data": body})

    # ==================================================================================
    #  Wait for simulation result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
