"""Base component definition.

Wraps a class reference or factory with metadata (name, scope, properties,
lifecycle hooks). Usually created via convenience subclasses: Singleton,
Prototype.

Example::

    Component({'reference': MyClass, 'name': 'my_class', 'scope': 'singleton'})
"""

import inspect


class Component:
    """Base component definition for the CDI container."""

    def __init__(self, options):
        # Accept a raw class as shorthand — wrap it in a dict
        if inspect.isclass(options):
            options = {"reference": options}
        elif not isinstance(options, dict):
            # For callable factories passed directly
            options = {"reference": options}

        # The class / callable that will be instantiated.
        # If a factory or wire_factory is present and no explicit reference,
        # leave reference as None.
        self.reference = options.get(
            "reference",
            options.get(
                "Reference",
                None if (options.get("factory") or options.get("wire_factory") or options.get("wireFactory"))
                else None,
            ),
        )

        self.name = options.get("name")
        self.qualifier = options.get("qualifier")
        self.scope = options.get("scope")
        self.properties = options.get("properties")
        self.profiles = options.get("profiles")
        self.primary = options.get("primary")
        self.factory = options.get("factory")
        self.factory_function = options.get("factory_function") or options.get("factoryFunction")
        self.factory_args = options.get("factory_args") or options.get("factoryArgs")
        self.wire_factory = options.get("wire_factory") or options.get("wireFactory")
        self.constructor_args = options.get("constructor_args") or options.get("constructorArgs")
        self.depends_on = options.get("depends_on") or options.get("dependsOn")

        # Runtime state
        self.is_active = True
        self.instance = None
        self.is_class = False
