import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pydbc_sqlite  # noqa: F401
from boot import Boot
from cdi import Context, Singleton
from boot_pydbc import pydbc_auto_configuration, DataSourceBuilder
from boot_flyway import ManagedFlyway, flyway_starter

from services import NoteRepository, TagRepository, Application

# ── Secondary datasource (tags DB) ────────────────────────────────────────
# Reads from boot.datasource-tags.* config.
# Bean names: tags_data_source, tags_pydbc_template, etc.
tags_ds_components = (
    DataSourceBuilder.create()
    .prefix('boot.datasource-tags')
    .bean_names({
        'data_source': 'tags_data_source',
        'pydbc_template': 'tags_pydbc_template',
        'named_parameter_pydbc_template': 'tags_named_pydbc_template',
        'schema_initializer': 'tags_schema_initializer',
    })
    .without_schema_initializer()  # Flyway owns the tags schema
    .build()
)

# ── Primary Flyway runner (notes DB) ──────────────────────────────────────
# Default prefix boot.flyway / default bean name managed_flyway
notes_flyway = flyway_starter()

# ── Secondary Flyway runner (tags DB) ────────────────────────────────────
# Custom prefix boot.flyway-tags; wired to tags_data_source;
# explicitly named managed_flyway_tags so it coexists with managed_flyway.
tags_flyway = flyway_starter(
    prefix='boot.flyway-tags',
    datasource_bean='tags_data_source',
)
# Rename the managed_flyway singleton produced by flyway_starter to
# managed_flyway_tags so both Flyway runners can live in one context.
from cdi import Singleton as _S
_renamed = []
for comp in tags_flyway:
    if comp.name == 'managed_flyway':
        # Re-create a Singleton with the new name, same reference and wiring
        _renamed.append(_S({
            'reference': comp.reference,
            'name': 'managed_flyway_tags',
            'depends_on': 'tags_data_source',
            'properties': [{'name': 'data_source', 'reference': 'tags_data_source'}],
        }))
    else:
        _renamed.append(comp)
tags_flyway = _renamed

Boot.boot({
    'contexts': [
        Context(
            pydbc_auto_configuration()   # primary datasource + template
            + tags_ds_components          # secondary datasource + template
            + notes_flyway                # managed_flyway (notes)
            + tags_flyway,                # managed_flyway_tags (tags)
        ),
        Context([
            Singleton(NoteRepository),
            Singleton(TagRepository),
            Singleton(Application),
        ]),
    ]
})
