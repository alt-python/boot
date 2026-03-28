import re


class AzureFunctionControllerRegistrar:
    """
    Scans CDI components for route metadata and builds a routeKey → handler dict
    for Azure Function dispatch.

    Two patterns supported:

    1. Declarative: class-level __routes__ attribute
       class TodoController:
           __routes__ = [
               {'method': 'GET', 'path': '/todos', 'handler': 'list'},
               {'method': 'GET', 'path': '/todos/{id}', 'handler': 'get_by_id'},
           ]

    2. Imperative: routes(routes, ctx) method
       class TodoController:
           def routes(self, routes, ctx):
               routes['GET /custom'] = {'handler': lambda req: {'custom': True}}
    """

    def __init__(self):
        self.route_count = 0

    def register(self, routes: dict, ctx) -> None:
        """
        Scan ctx.components and populate the routes dict.

        Paths are normalised to colon-style (``/users/:id``) for segment-based
        matching regardless of whether the declaration uses ``{id}`` or ``:id``.

        :param routes: dict to populate with ``'METHOD /path'`` → ``{'handler': callable}``
        :param ctx: CDI application context
        :raises ValueError: if a declared handler method does not exist on the instance
        """
        self.route_count = 0
        components = ctx.components

        for name, comp in components.items():
            if not comp["instance"]:
                continue

            instance = comp["instance"]
            ref = comp["reference"]

            # Pattern 1: declarative __routes__ metadata
            declared_routes = getattr(ref, "__routes__", None) if ref is not None else None
            if declared_routes is not None and isinstance(declared_routes, list):
                for route in declared_routes:
                    method = route["method"]
                    path = route["path"]
                    handler_name = route["handler"]

                    bound = getattr(instance, handler_name, None)
                    if not callable(bound):
                        raise ValueError(
                            f"Controller ({name}) declares route {method} {path} "
                            f"→ {handler_name}() but the method does not exist"
                        )

                    # Normalise {param} → :param for segment matching
                    colon_path = re.sub(r"\{(\w+)\}", r":\1", path)
                    route_key = f"{method.upper()} {colon_path}"

                    routes[route_key] = {"handler": bound}
                    self.route_count += 1

            # Pattern 2: imperative routes(routes, ctx) method
            elif callable(getattr(instance, "routes", None)) and declared_routes is None:
                instance.routes(routes, ctx)
