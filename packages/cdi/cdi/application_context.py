"""ApplicationContext — Spring-inspired synchronous IoC container.

Lifecycle phases (D004):
  parse_contexts → create_singletons → inject_singleton_dependencies
  → initialise_singletons → register_singleton_destroyers → run

Injection modes (D002):
  1. Null-property autowiring  — ``self.x = None`` → look up 'x' in context
  2. Placeholder resolution    — ``self.x = '${some.path}'`` → config.get()
  3. Explicit Property wiring  — Component(properties=[Property(...)])
"""

from __future__ import annotations

import inspect
import os
import re
import signal

from .component import Component
from .context import Context
from .property import Property
from .scopes import Scopes

# Sentinel used to distinguish "no default provided" from None.
_UNSET = object()


def _to_snake(name: str) -> str:
    """Convert PascalCase/CamelCase class name to snake_case component name.

    Examples:
        GreetingRepository → greeting_repository
        MyService          → my_service
        HTTPClient         → h_t_t_p_client  (acceptable approximation)
    """
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class ApplicationContext:
    """Spring-inspired IoC application context for Python.

    Constructor options (flexible):
        ApplicationContext()                   — empty context
        ApplicationContext(ctx)                — single Context
        ApplicationContext([ctx1, ctx2])        — list of Contexts
        ApplicationContext({'contexts': [...], 'config': cfg, 'profiles': 'p1,p2'})
    """

    DEFAULT_CONTEXT_NAME = "default"

    def __init__(self, options=None):
        # ---- normalise options → self.contexts --------------------------------
        if options is None:
            contexts_raw = []
        elif isinstance(options, list):
            contexts_raw = options
        elif isinstance(options, dict):
            raw = options.get("contexts")
            if raw is None:
                contexts_raw = []
            elif isinstance(raw, list):
                contexts_raw = raw
            else:
                contexts_raw = [raw]
        elif isinstance(options, Context):
            contexts_raw = [options]
        elif isinstance(options, Component):
            contexts_raw = [Context([options])]
        elif inspect.isclass(options):
            contexts_raw = [Context([Component(options)])]
        else:
            # plain object / dict-like — treat as a single component definition
            if hasattr(options, "__dict__"):
                contexts_raw = [options]
            else:
                contexts_raw = [options]

        self.contexts = contexts_raw

        # ---- profiles ---------------------------------------------------------
        if isinstance(options, dict):
            profiles_opt = options.get("profiles")
        else:
            profiles_opt = None
        self.profiles = (
            profiles_opt
            or os.environ.get("PY_ACTIVE_PROFILES", "")
            or ""
        )

        # ---- name / config ----------------------------------------------------
        self.name = (
            (options.get("name") if isinstance(options, dict) else None)
            or self.DEFAULT_CONTEXT_NAME
        )

        if isinstance(options, dict):
            config_opt = options.get("config")
        else:
            config_opt = None

        if config_opt is not None:
            self._config = config_opt
        else:
            # Deferred to parse_contexts so the config package import is lazy.
            self._config = None

        # ---- internal registry ------------------------------------------------
        self.components: dict = {}
        self._creation_stack: list[str] = []

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def start(self, run: bool | dict = True) -> None:  # synchronous
        """Run the full lifecycle synchronously.

        Args:
            run: If False (or dict with run=False), skips the run phase.
        """
        _run = run if isinstance(run, bool) else run.get("run", True)
        self.parse_contexts()
        self.create_singletons()
        self.inject_singleton_dependencies()
        self.initialise_singletons()
        self.register_singleton_destroyers()
        if _run:
            self.run()

    # ------------------------------------------------------------------
    # Phase 1: parse_contexts
    # ------------------------------------------------------------------

    def parse_contexts(self) -> None:
        """Parse all context definitions into the internal component registry."""
        self._ensure_config()

        for ctx in self.contexts:
            if ctx is None:
                raise ValueError(
                    f"ApplicationContext ({self.name}) received a nullish context."
                )
            self._parse_context(ctx)

        # Auto-register infrastructure components (first-write-wins).
        self._register_infra_components()

    def _ensure_config(self) -> None:
        """Lazily resolve the config object so imports stay localised."""
        if self._config is None:
            try:
                from config import EphemeralConfig  # type: ignore
                self._config = EphemeralConfig({})
            except ImportError:
                from config.ephemeral_config import EphemeralConfig
                self._config = EphemeralConfig({})

    def _parse_context(self, ctx) -> None:
        """Dispatch a single item from self.contexts to the component parser."""
        if isinstance(ctx, Context):
            for comp in (ctx.components or []):
                self._derive_context_component(comp)
        elif isinstance(ctx, (Component,)):
            self._parse_context_component(ctx)
        elif isinstance(ctx, dict):
            # Plain-dict component spec (has at least a 'name' or 'Reference').
            self._derive_context_component(ctx)
        elif inspect.isclass(ctx):
            self._parse_context_component(Component(ctx))
        else:
            # Treat as a raw object spec dict equivalent
            self._derive_context_component(ctx)

    def _derive_context_component(self, spec) -> None:
        """Normalise a raw spec to a Component and register it."""
        if isinstance(spec, (Component,)):
            self._parse_context_component(spec)
        elif isinstance(spec, dict):
            self._parse_context_component(Component(spec))
        elif inspect.isclass(spec):
            self._parse_context_component(Component(spec))
        else:
            # Object instance passed as spec — unusual but handle gracefully
            self._parse_context_component(Component({"reference": spec}))

    def _parse_context_component(self, comp: Component) -> None:
        """Register one component definition into self.components."""
        ref = comp.reference
        is_class = inspect.isclass(ref)

        # Derive the name
        if comp.name:
            raw_name = comp.name
        elif is_class:
            raw_name = ref.__name__
        else:
            # Fallback for plain-object instances used as singletons
            raw_name = type(ref).__name__ if ref is not None else "unknown"

        name = _to_snake(raw_name)

        # Normalise profiles → list[str]
        profiles = comp.profiles or (getattr(ref, "profiles", None) if is_class else None) or []
        if isinstance(profiles, str):
            profiles = [p.strip() for p in profiles.split(",") if p.strip()]

        # Determine if active under current active profiles
        active_profiles = [p.strip() for p in self.profiles.split(",") if p.strip()]
        if not profiles:
            is_active = True
        elif not active_profiles:
            # Component has profiles but no active profiles set → inactive
            is_active = False
        else:
            # Positive match: any profile in active_profiles
            positives = [p for p in profiles if not p.startswith("!")]
            negations = [p[1:] for p in profiles if p.startswith("!")]

            positive_match = any(p in active_profiles for p in positives)
            negation_match = bool(negations) and not any(n in active_profiles for n in negations)

            if positives and negations:
                is_active = positive_match or negation_match
            elif positives:
                is_active = positive_match
            else:
                # Only negations
                is_active = negation_match

        if not is_active:
            return  # skip silently

        # Build the internal record
        scope = (
            comp.scope
            or (getattr(ref, "scope", None) if is_class else None)
            or Scopes.SINGLETON
        )

        qualifier = comp.qualifier or (getattr(ref, "qualifier", None) if is_class else None)

        depends_on = comp.depends_on
        if isinstance(depends_on, str):
            depends_on = [depends_on]

        record = {
            "name": name,
            "qualifier": qualifier,
            "scope": scope,
            "reference": ref,
            "is_class": is_class,
            "properties": comp.properties,
            "profiles": profiles,
            "is_active": is_active,
            "factory": comp.factory,
            "factory_function": comp.factory_function,
            "factory_args": comp.factory_args,
            "wire_factory": comp.wire_factory,
            "constructor_args": comp.constructor_args,
            "depends_on": depends_on,
            "primary": comp.primary or False,
            "instance": None,
        }

        existing = self.components.get(name)
        if existing is None:
            self.components[name] = record
        elif record["primary"] and not existing["primary"]:
            self.components[name] = record
        elif not record["primary"] and existing["primary"]:
            pass  # skip non-primary duplicate
        else:
            raise ValueError(
                f"Duplicate definition of application context component ({name})"
            )

    def _register_infra_components(self) -> None:
        """Register logger_factory, logger, and config if not already present."""
        if "logger_factory" not in self.components:
            from logger.logger_factory import LoggerFactory  # type: ignore
            lf = LoggerFactory(config=self._config)
            self.components["logger_factory"] = {
                "name": "logger_factory",
                "qualifier": None,
                "scope": Scopes.SINGLETON,
                "reference": lf,
                "is_class": False,
                "properties": [],
                "profiles": [],
                "is_active": True,
                "factory": None,
                "factory_function": None,
                "factory_args": None,
                "wire_factory": None,
                "constructor_args": None,
                "depends_on": None,
                "primary": False,
                "instance": lf,  # pre-instantiated
            }

        if "logger" not in self.components:
            self.components["logger"] = {
                "name": "logger",
                "qualifier": None,
                "scope": Scopes.PROTOTYPE,
                "reference": None,
                "is_class": False,
                "properties": [],
                "profiles": [],
                "is_active": True,
                "factory": None,
                "factory_function": "get_logger",
                "factory_args": None,
                "wire_factory": "logger_factory",
                "constructor_args": None,
                "depends_on": None,
                "primary": False,
                "instance": None,
            }

        if "config" not in self.components:
            self.components["config"] = {
                "name": "config",
                "qualifier": None,
                "scope": Scopes.SINGLETON,
                "reference": self._config,
                "is_class": False,
                "properties": [],
                "profiles": [],
                "is_active": True,
                "factory": None,
                "factory_function": None,
                "factory_args": None,
                "wire_factory": None,
                "constructor_args": None,
                "depends_on": None,
                "primary": False,
                "instance": self._config,  # pre-instantiated
            }

    # ------------------------------------------------------------------
    # Phase 2: create_singletons
    # ------------------------------------------------------------------

    def create_singletons(self) -> None:
        """Instantiate all singleton components."""
        self._creation_stack = []
        for comp in list(self.components.values()):
            if comp["scope"] == Scopes.SINGLETON and comp["instance"] is None:
                self._create_singleton(comp)
        self._creation_stack = []

    def _create_singleton(self, comp: dict) -> None:
        """Instantiate a single singleton (recursive for constructor-arg deps)."""
        name = comp["name"]
        if name in self._creation_stack:
            cycle = " → ".join(self._creation_stack + [name])
            raise RuntimeError(f"Circular dependency detected: {cycle}")
        self._creation_stack.append(name)

        ref = comp["reference"]
        if comp["is_class"]:
            ctor_args = comp.get("constructor_args")
            if ctor_args:
                if not isinstance(ctor_args, list):
                    ctor_args = [ctor_args]
                resolved = []
                for arg in ctor_args:
                    if isinstance(arg, str) and arg in self.components:
                        dep = self.components[arg]
                        if dep["scope"] == Scopes.SINGLETON and dep["instance"] is None:
                            self._create_singleton(dep)
                        resolved.append(dep["instance"] if dep["instance"] is not None else dep["reference"])
                    else:
                        resolved.append(arg)
                comp["instance"] = ref(*resolved)
            else:
                comp["instance"] = ref()
        elif callable(comp.get("factory")):
            factory = comp["factory"]
            args = comp.get("factory_args")
            if not isinstance(args, list):
                args = [args] if args is not None else []
            comp["instance"] = factory(*args)
        else:
            # ref is already an instance (e.g. config object, pre-built singleton)
            comp["instance"] = ref

        self._creation_stack.pop()

    # ------------------------------------------------------------------
    # Phase 3: inject_singleton_dependencies
    # ------------------------------------------------------------------

    def inject_singleton_dependencies(self) -> None:
        """Autowire and explicitly wire all singleton instances."""
        for comp in self.components.values():
            if comp["scope"] == Scopes.SINGLETON and comp["instance"] is not None:
                self._autowire_component_dependencies(comp["instance"], comp)
                self._wire_component_dependencies(comp)

    def _resolve_config_placeholder(self, placeholder: str) -> object:
        """Resolve ``${some.path:default}`` against self._config."""
        inner = placeholder[2:-1]  # strip ${ and }
        if ":" in inner:
            path, raw_default = inner.split(":", 1)
            try:
                default = int(raw_default)
            except ValueError:
                try:
                    default = float(raw_default)
                except ValueError:
                    default = raw_default
        else:
            path = inner
            default = _UNSET

        try:
            if default is _UNSET:
                return self._config.get(path)
            else:
                return self._config.get(path, default)
        except KeyError:
            raise KeyError(
                f"Failed to resolve placeholder component property value ({path}) from config."
            )

    def _autowire_component_dependencies(self, instance: object, comp: dict) -> None:
        """Autowire instance attributes by name-lookup and placeholder resolution.

        Iterates ``vars(instance)`` so only __init__-set attributes are considered.
        """
        for prop_name, value in list(vars(instance).items()):
            self._wire_component_property_by_name(instance, comp, prop_name, value)

    def _wire_component_property_by_name(
        self, instance: object, comp: dict, prop_name: str, value: object
    ) -> None:
        """Wire a single attribute discovered via vars()."""
        if value is None:
            # Null-property autowiring: look up component by name; skip silently if missing
            resolved = self.get(prop_name, None, comp)
            if resolved is not None:
                setattr(instance, prop_name, resolved)
        elif isinstance(value, str) and value.startswith("${"):
            # Placeholder resolution
            try:
                setattr(instance, prop_name, self._resolve_config_placeholder(value))
            except KeyError as exc:
                raise KeyError(
                    f"Failed to explicitly autowired placeholder component "
                    f"({comp['name']}) property value ({prop_name}) from config."
                ) from exc

    def _wire_component_dependencies(self, comp: dict) -> None:
        """Apply explicit Property definitions from the component record."""
        props = comp.get("properties")
        if not props:
            return
        if not isinstance(props, list):
            props = [props]
        for prop in props:
            self._wire_one_property(comp, prop)

    def _wire_one_property(self, comp: dict, prop) -> None:
        """Apply a single Property (or property-dict) to the component instance."""
        if not isinstance(prop, Property):
            p = Property(prop if isinstance(prop, dict) else {"name": prop})
        else:
            p = prop

        if not isinstance(p.name, str):
            return

        instance = comp["instance"]
        if p.reference:
            setattr(instance, p.name, self.get(p.reference, None, comp))
        if p.value is not None:
            setattr(instance, p.name, p.value)
        if p.path:
            default = p.default_value if p.default_value is not None else _UNSET
            if default is _UNSET:
                setattr(instance, p.name, self._config.get(p.path))
            else:
                setattr(instance, p.name, self._config.get(p.path, default))

    # ------------------------------------------------------------------
    # Phase 4: initialise_singletons
    # ------------------------------------------------------------------

    def _topological_sort(self) -> list[str]:
        """Kahn's algorithm over singleton components respecting depends_on."""
        keys = [
            k for k, v in self.components.items() if v["scope"] == Scopes.SINGLETON
        ]

        # Validate all depends_on targets exist
        for key in keys:
            deps = self.components[key].get("depends_on") or []
            if isinstance(deps, str):
                deps = [deps]
            for dep in deps:
                if dep not in self.components:
                    raise ValueError(
                        f"Component ({key}) dependsOn ({dep}) which does not exist in the context"
                    )

        # Build graph (edge: dep → dependent means dep must come first)
        graph: dict[str, list[str]] = {k: [] for k in keys}
        in_degree: dict[str, int] = {k: 0 for k in keys}

        for key in keys:
            deps = self.components[key].get("depends_on") or []
            if isinstance(deps, str):
                deps = [deps]
            for dep in deps:
                if dep in graph:
                    graph[dep].append(key)
                    in_degree[key] += 1

        # Kahn's BFS
        queue = [k for k in keys if in_degree[k] == 0]
        sorted_keys: list[str] = []
        while queue:
            node = queue.pop(0)
            sorted_keys.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_keys) != len(keys):
            remaining = [k for k in keys if k not in sorted_keys]
            raise RuntimeError(
                f"Circular dependsOn detected involving: {', '.join(remaining)}"
            )

        return sorted_keys

    def initialise_singletons(self) -> None:
        """Call set_application_context() then init() on singletons in dep order."""
        for key in self._topological_sort():
            comp = self.components[key]
            instance = comp["instance"]
            if instance is None:
                continue
            if callable(getattr(instance, "set_application_context", None)):
                instance.set_application_context(self)
            if callable(getattr(instance, "init", None)):
                instance.init()

    # ------------------------------------------------------------------
    # Phase 5: register_singleton_destroyers
    # ------------------------------------------------------------------

    def register_singleton_destroyers(self) -> None:
        """Register stop/destroy lifecycle hooks on SIGINT."""
        for comp in self.components.values():
            if comp["scope"] != Scopes.SINGLETON:
                continue
            instance = comp["instance"]
            if instance is None:
                continue
            if callable(getattr(instance, "stop", None)):
                self._register_signal_handler(lambda inst=instance: inst.stop())
            if callable(getattr(instance, "destroy", None)):
                self._register_signal_handler(lambda inst=instance: inst.destroy())

    @staticmethod
    def _register_signal_handler(handler) -> None:
        """Attach handler to SIGINT, suppressing errors in non-main threads."""
        try:
            prev = signal.getsignal(signal.SIGINT)

            def combined(signum, frame):
                handler()
                if callable(prev):
                    prev(signum, frame)

            signal.signal(signal.SIGINT, combined)
        except (OSError, ValueError):
            pass  # non-main thread or signal not available

    # ------------------------------------------------------------------
    # Phase 6: run
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Call start() then run() on singletons that implement those methods."""
        for comp in self.components.values():
            if comp["scope"] != Scopes.SINGLETON:
                continue
            instance = comp["instance"]
            if instance is None:
                continue
            if callable(getattr(instance, "start", None)):
                # Guard against calling our own start() recursively
                if instance is not self:
                    instance.start()
            if callable(getattr(instance, "run", None)):
                if instance is not self:
                    instance.run()

    # ------------------------------------------------------------------
    # get() — retrieve a component by name
    # ------------------------------------------------------------------

    def get(self, reference: str, default=_UNSET, target_args=None) -> object:
        """Retrieve a component instance.

        Args:
            reference:   Component name (snake_case).
            default:     Returned if component not found; KeyError raised if absent.
            target_args: Passed to prototype factory functions (qualifier context).

        Returns:
            The component instance (singleton) or a fresh instance (prototype).
        """
        comp = self.components.get(reference)
        if comp is None:
            if default is not _UNSET:
                return default
            raise KeyError(f"Failed component reference lookup for ({reference})")

        if comp["scope"] == Scopes.SINGLETON:
            return comp["instance"]

        # ---------- Prototype scope ----------
        if comp["is_class"]:
            instance = comp["reference"]()
            self._autowire_component_dependencies(instance, comp)
            return instance

        # wire_factory + factory_function (e.g. logger)
        wire_factory = comp.get("wire_factory")
        factory_fn = comp.get("factory_function")
        if wire_factory and factory_fn:
            factory_inst = self.get(wire_factory)
            # Derive qualifier from target_args (the caller's component record)
            qualifier = None
            if isinstance(target_args, dict):
                qualifier = target_args.get("qualifier") or target_args.get("name")
            return getattr(factory_inst, factory_fn)(qualifier)

        # factory string + factory_function string
        factory_ref = comp.get("factory")
        if isinstance(factory_ref, str) and factory_fn:
            factory_inst = self.get(factory_ref)
            args = comp.get("factory_args")
            if not isinstance(args, list):
                args = [args] if args is not None else []
            return getattr(factory_inst, factory_fn)(*args)

        # callable factory
        if callable(factory_ref):
            args = target_args or comp.get("factory_args")
            if not isinstance(args, list):
                args = [args] if args is not None else []
            instance = factory_ref(*args)
            if hasattr(instance, "__dict__"):
                self._autowire_component_dependencies(instance, comp)
            return instance

        # Plain reference prototype (non-class callable or object)
        ref = comp["reference"]
        if callable(ref):
            args = target_args or comp.get("factory_args")
            if not isinstance(args, list):
                args = [args] if args is not None else []
            instance = ref(*args)
            if hasattr(instance, "__dict__"):
                self._autowire_component_dependencies(instance, comp)
            return instance

        # Fallback: return the reference directly
        return ref
