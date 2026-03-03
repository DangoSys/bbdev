import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result

config = {
    "name": "Marshal Build",
    "description": "build marshal",
    "flows": ["marshal"],
    "triggers": [http("POST", "/marshal/build")],
    "enqueues": ["marshal.build"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    body = request.body or {}
    await ctx.enqueue({"topic": "marshal.build", "data": body})
    # ==================================================================================
    #  Wait for result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
