import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result

config = {
    "name": "Marshal Launch",
    "description": "launch marshal",
    "flows": ["marshal"],
    "triggers": [http("POST", "/marshal/launch")],
    "enqueues": ["marshal.launch"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    body = request.body or {}
    await ctx.enqueue({"topic": "marshal.launch", "data": body})

    # ==================================================================================
    #  Wait for result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
