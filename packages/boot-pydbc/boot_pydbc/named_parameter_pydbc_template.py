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

    def update(self, sql, param_map=None):
        norm_sql, params = ParamstyleNormalizer.normalize(sql, param_map or {}, 'qmark')
        return self._template.update(norm_sql, params)

    def execute(self, sql):
        return self._template.execute(sql)
