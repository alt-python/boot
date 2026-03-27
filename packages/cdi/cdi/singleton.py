"""Singleton-scoped component — one shared instance per ApplicationContext."""

import inspect

from .component import Component
from .scopes import Scopes


class Singleton(Component):
    """Singleton-scoped component.

    Accepts either a class reference directly or an options dict.  If the
    argument is a plain class (not already an options dict containing
    ``reference``, ``factory``, or ``wire_factory``), it is normalised to
    ``{'reference': arg}``.
    """

    def __init__(self, options_arg):
        if inspect.isclass(options_arg):
            options = {"reference": options_arg}
        elif isinstance(options_arg, dict) and (
            options_arg.get("reference")
            or options_arg.get("Reference")
            or options_arg.get("factory")
            or options_arg.get("wire_factory")
            or options_arg.get("wireFactory")
        ):
            options = options_arg
        else:
            options = {"reference": options_arg}

        options["scope"] = Scopes.SINGLETON
        super().__init__(options)
