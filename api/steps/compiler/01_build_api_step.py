import asyncio

from motia import ApiRequest, ApiResponse, FlowContext, http

from utils.event_common import wait_for_result

config = {
    "name": "Build Compiler",
    "description": "build bitstream",
    "flows": ["compiler"],
    "triggers": [http("POST", "/compiler/build")],
    "enqueues": ["compiler.build"],
}


async def handler(request: ApiRequest, ctx: FlowContext) -> ApiResponse:
    body = request.body or {}
    await ctx.enqueue({"topic": "compiler.build", "data": body})

    # ==================================================================================
    #  Wait for build result
    # ==================================================================================
    while True:
        result = await wait_for_result(ctx)
        if result is not None:
            return result
        await asyncio.sleep(1)
