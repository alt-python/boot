"""Property definition — binds a config value to a component property.

Supports both explicit value assignment and placeholder-based resolution
against the active config object (``path`` / ``default_value`` pair).
"""


class Property:
    """Describes a property injection point on a component.

    Attributes:
        name: The attribute name on the target component instance.
        reference: Optional component name to look up from the context.
        value: An explicit value to assign directly.
        path: A config path (dot-notation) used for placeholder resolution.
        default_value: Fallback when the config path is absent.
    """

    def __init__(self, options):
        self.name = options.get("name")
        self.reference = options.get("ref") or options.get("reference")
        self.value = options.get("value")
        self.path = options.get("path")
        self.default_value = options.get("default_value") or options.get("defaultValue")
