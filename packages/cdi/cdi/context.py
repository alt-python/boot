"""Context — a named collection of component definitions.

Passed to ApplicationContext to declare the beans that should be managed.

Example::

    ctx = Context([Singleton(MyService), Singleton(MyRepo)])
"""


class Context:
    """A named, profile-aware collection of component definitions."""

    def __init__(self, components=None, profile=None):
        components = components or []
        if not isinstance(components, list):
            components = [components]
        self.components = components
        self.profile = profile
