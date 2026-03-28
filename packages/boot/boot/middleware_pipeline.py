import asyncio
import inspect


class MiddlewarePipeline:
    @staticmethod
    def collect(application_context):
        components = application_context.components
        middlewares = []
        for name, comp in components.items():
            if not comp["instance"]:
                continue
            ref = comp["reference"]
            mw_meta = getattr(ref, "__middleware__", None) if ref is not None else None
            if mw_meta is not None:
                order = mw_meta.get("order", float("inf")) if isinstance(mw_meta, dict) else float("inf")
                middlewares.append({"instance": comp["instance"], "order": order})
        middlewares.sort(key=lambda m: m["order"])
        return [m["instance"] for m in middlewares]

    @staticmethod
    def compose(middleware_instances, final_handler):
        chain = list(middleware_instances)

        async def dispatch(index, request):
            if index == len(chain):
                result = final_handler(request)
                if inspect.isawaitable(result):
                    result = await result
                return result
            middleware = chain[index]

            async def next_fn(next_request=None):
                return await dispatch(index + 1, next_request if next_request is not None else request)

            result = middleware.handle(request, next_fn)
            if inspect.isawaitable(result):
                result = await result
            return result

        async def pipeline(request):
            return await dispatch(0, request)

        return pipeline
