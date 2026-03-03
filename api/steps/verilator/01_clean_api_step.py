import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result

config = {
    "name": "Verilator Clean",
    "description": "clean build directory",
    "flows": ["verilator"],
    "triggers": [http("POST", "/verilator/clean")],
    "enqueues": ["verilator.clean"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    body = request.body or {}
    await ctx.enqueue({"topic": "verilator.clean", "data": {**body, "task": "clean"}})

    # ==================================================================================
    #  Wait for simulation result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
