# Spring Comparison

A guide for developers coming from Spring Framework and Spring Boot. This maps
Spring concepts to their alt-python equivalents, notes what is similar, what
differs, and where the framework makes deliberately different choices.

## Core Concept Mapping

| Spring | alt-python | Notes |
|---|---|---|
| `ApplicationContext` | `ApplicationContext` | Same name, synchronous lifecycle |
| `@Component` / `@Service` | `Singleton(MyClass)` | No annotations — use helper classes |
| `@Autowired` (field) | `self.my_bean = None` | Property name matches component name |
| `@Value("${path:default}")` | `self.port = '${server.port:8080}'` | Resolved during CDI wiring |
| `@Profile` | `profiles = ['dev']` class attribute | Same concept |
| `@Primary` | `primary = True` class attribute | Same behaviour |
| `@DependsOn` | `depends_on = ['other_bean']` class attribute | Topological sort |
| `@PostConstruct` | `def init(self)` | Convention, not annotation |
| `@PreDestroy` | `def destroy(self)` | Convention, not annotation |
| `ApplicationContextAware` | `def set_application_context(self, ctx)` | Convention-based detection |
| `ApplicationContext.refresh()` | `ctx.start()` | Synchronous in Python |
| `ApplicationContext.getBean()` | `ctx.get('bean_name')` | snake_case name |
| Prototype scope | `Prototype(MyClass)` | New instance per `ctx.get()` |
| `BeanPostProcessor` | `BeanPostProcessor` | Same interface |
| `ApplicationEvent` | CDI event bus | `onApplicationEvent()` method convention |
| `Environment` / `PropertySource` | `PropertySourceChain` / `EnvPropertySource` | |
| `application.properties` / `.yaml` | Same — identical file format | |
| `SPRING_PROFILES_ACTIVE` | `PY_ACTIVE_PROFILES` | Renamed for Python environments |
| `spring.profiles.active` | `PY_ACTIVE_PROFILES` | |
| `@EnableAutoConfiguration` / starters | `pydbc_auto_configuration()`, `lambda_starter()`, etc. | Function-based |
| Spring Security `FilterChain` | `MiddlewarePipeline` | `__middleware__ = {"order": N}` |
| `Filter.doFilter(req, res, chain)` | `async def handle(self, request, next_fn)` | |
| `JdbcTemplate` | `PydbcTemplate` | Synchronous |
| `NamedParameterJdbcTemplate` | `NamedParameterPydbcTemplate` | Same `:param` syntax |
| `DataSource` auto-config | `pydbc_auto_configuration()` | Reads `boot.datasource.*` |
| Flyway integration | `flyway` / `boot-flyway` packages | Synchronous `init()` |
| Spring MVC `@RestController` | Controller with `__routes__` | Declarative route metadata |
| `@GetMapping` / `@PostMapping` | `{'method': 'GET', 'path': '/', 'handler': 'method'}` | |
| `@PathVariable` | `request['params']['id']` | Normalised request dict |
| `@RequestBody` | `request['body']` | Normalised request dict |
| `SpringApplication.run()` | `Boot.boot()` | |
| Spring Boot startup banner | `print_banner()` | `boot.banner-mode: off` to suppress |

## What Is Similar

**IoC container lifecycle.** The parse → wire → init → run → destroy flow maps
closely to Spring's refresh cycle. `BeanPostProcessor`, lifecycle callbacks, and
application events work the same way conceptually.

**Property injection.** `self.my_service = None` autowiring is analogous to
`@Autowired` field injection. The container matches by name (not type — Python
CDI uses naming convention).

**Externalized configuration.** Profile-based file loading
(`application-{profile}.yaml`), environment variable binding, and layered
precedence follow Spring Boot's model directly. The `.properties` file parser
handles the same format including array notation.

**Startup banner.** `Boot.boot()` prints a startup banner by default. Set
`boot.banner-mode: off` in config, or use `Boot.test()` to suppress it in
tests.

**Flyway.** The `flyway` and `boot-flyway` packages mirror Spring Boot's Flyway
auto-configuration. Config keys follow the same naming pattern
(`boot.flyway.locations`, `boot.flyway.validate-on-migrate`).

## What Is Different

### No annotations

Python has no stable annotation equivalent for Spring-style component scanning.
The framework uses:

- **Helper classes** (`Singleton(MyClass)`) instead of `@Component`
- **Convention methods** (`init()`, `destroy()`) instead of `@PostConstruct`,
  `@PreDestroy`
- **Class attributes** (`profiles`, `primary`, `depends_on`) instead of
  `@Profile`, `@Primary`, `@DependsOn`

### Name-based wiring, not type-based

Spring resolves autowiring by type. alt-python wires by name:

```python
class OrderService:
    def __init__(self):
        self.order_repository = None  # injected if 'order_repository' is registered
```

The property name is the qualifier. There is no `@Qualifier` equivalent because
the name already serves that purpose. Class names are converted to `snake_case`:
`OrderRepository` → `order_repository`.

### Synchronous CDI lifecycle

Spring's `ApplicationContext` is designed around an async-capable world, and
Spring Boot integrates with reactive runtimes. Python's CDI runtime is
synchronous throughout — `start()`, `init()`, and `destroy()` are all plain
function calls, not coroutines.

This has one significant consequence: lifecycle methods (`init()`, `destroy()`)
must be declared as `def`, not `async def`. Use `asyncio.run()` to bridge when
async backend calls are needed. See
[ADR-012](decisions/ADR-012-cdi-lifecycle-methods-synchronous.md).

The benefit: `ManagedFlyway.migrate()` completes inside `init()`, so downstream
beans can query the schema immediately — no `ready()` call needed. See
[ADR-013](decisions/ADR-013-managed-flyway-synchronous-init.md).

### No classpath scanning

Spring scans the classpath to discover `@Component` classes. Python has no
classpath. Pass classes explicitly to `Context()`:

```python
context = Context([Singleton(UserService), Singleton(UserRepository)])
```

### Environment variable naming

Spring uses `SPRING_PROFILES_ACTIVE`. alt-python uses `PY_ACTIVE_PROFILES` and
`PY_CONFIG_PASSPHRASE`. The `PY_` prefix avoids confusion in environments where
both Node.js and Python processes run. See
[ADR-002](decisions/ADR-002-env-var-naming.md).

### Logger category separator

Spring (and the JS port) uses slash-separated category names
(`/com/example/MyService`). Python uses dot-separated names
(`com.example.MyService`), matching the stdlib `logging` convention. Log level
config keys use nested dicts, not flat dotted strings. See
[ADR-003](decisions/ADR-003-logger-category-separator.md) and
[ADR-008](decisions/ADR-008-config-level-keys.md).

### pysypt DES interop

`PBEWITHMD5ANDDES` encrypted values from a Java Spring Boot application cannot
be decrypted by `pysypt` due to a DES emulation difference. Use
`PBEWITHHMACSHA256ANDAES_256` for new deployments requiring cross-language
interoperability. See [ADR-005](decisions/ADR-005-pbe1-des-emulation.md).

## Migrating from Spring

1. **Your mental model transfers.** IoC, DI, lifecycle, events — the concepts
   are the same. The syntax changes.

2. **Replace annotations with definitions.** Where you'd write
   `@Service public class Foo`, write `Singleton(Foo)` in the `Context`.

3. **Replace `@Autowired` with null properties.** Initialise injectable fields
   to `None` in `__init__`. Name them after the bean they should receive.

4. **Replace `application.properties` as-is.** The same file format works. Set
   `PY_ACTIVE_PROFILES` instead of `SPRING_PROFILES_ACTIVE`.

5. **Use `init()` for `@PostConstruct`.** No annotation — the container calls
   it automatically. Declare it as regular `def`, not `async def`.

6. **Think in names, not types.** Property names are qualifiers. The property
   name determines which bean is injected.

7. **Use `Boot.boot()` instead of `SpringApplication.run()`.** It loads config,
   prints the banner, registers CDI beans for `config` and `logger_factory`,
   and calls `application.run()`.
