from pydbc_core import ParamstyleNormalizer
from boot_pydbc.pydbc_template import PydbcTemplate


class NamedParameterPydbcTemplate:
    def __init__(self, data_source):
        self._template = PydbcTemplate(data_source)

    def query_for_list(self, sql, param_map=None, row_mapper=None):
        norm_sql, params = ParamstyleNormalizer.normalize(sql, param_map or {}, 'qmark')
        return self._template.query_for_list(norm_sql, params, row_mapper)

    def query_for_object(self, sql, param_map=None, row_mapper=None):
        norm_sql, params = ParamstyleNormalizer.normalize(sql, param_map or {}, 'qmark')
        return self._template.query_for_object(norm_sql, params, row_mapper)

    def query_for_map(self, sql, param_map=None):
        """Execute a query expecting exactly one row, returned as a dict."""
        norm_sql, params = ParamstyleNormalizer.normalize(sql, param_map or {}, 'qmark')
        return self._template.query_for_map(norm_sql, params)

    def update(self, sql, param_map=None):
        norm_sql, params = ParamstyleNormalizer.normalize(sql, param_map or {}, 'qmark')
        return self._template.update(norm_sql, params)

    def batch_update(self, sql, param_maps):
        """Execute *sql* for each param_map in *param_maps*.

        Returns a list of affected row counts.
        """
        counts = []
        for pm in param_maps:
            norm_sql, params = ParamstyleNormalizer.normalize(sql, pm or {}, 'qmark')
            # Accumulate; use the underlying template's single-call path
            counts.append(self._template.update(norm_sql, params))
        return counts

    def execute(self, sql):
        return self._template.execute(sql)

    def execute_in_transaction(self, callback):
        """Execute *callback(tx)* inside a transaction.

        The callback receives a :class:`NamedTransactionTemplate` which
        accepts named-parameter maps.  Commits on success, rolls back on
        exception.
        """
        def _wrapped(tx):
            named_tx = NamedTransactionTemplate(tx)
            return callback(named_tx)
        return self._template.execute_in_transaction(_wrapped)


class NamedTransactionTemplate:
    """TransactionTemplate wrapper with :param_name SQL support."""

    def __init__(self, tx):
        self._tx = tx

    def query_for_list(self, sql, param_map=None, row_mapper=None):
        norm_sql, params = ParamstyleNormalizer.normalize(sql, param_map or {}, 'qmark')
        return self._tx.query_for_list(norm_sql, params, row_mapper)

    def query_for_object(self, sql, param_map=None, row_mapper=None):
        norm_sql, params = ParamstyleNormalizer.normalize(sql, param_map or {}, 'qmark')
        return self._tx.query_for_object(norm_sql, params, row_mapper)

    def query_for_map(self, sql, param_map=None):
        norm_sql, params = ParamstyleNormalizer.normalize(sql, param_map or {}, 'qmark')
        return self._tx.query_for_map(norm_sql, params)

    def update(self, sql, param_map=None):
        norm_sql, params = ParamstyleNormalizer.normalize(sql, param_map or {}, 'qmark')
        return self._tx.update(norm_sql, params)

    def execute(self, sql):
        return self._tx.execute(sql)
