class PydbcTemplate:
    def __init__(self, data_source):
        self._data_source = data_source

    def query_for_list(self, sql, params=(), row_mapper=None):
        conn = self._data_source.get_connection()
        try:
            pstmt = conn.prepare_statement(sql)
            for i, v in enumerate(params, 1):
                pstmt.set_parameter(i, v)
            rs = pstmt.execute_query()
            rows = rs.get_rows()
            rs.close()
            if row_mapper:
                return [row_mapper(row, i) for i, row in enumerate(rows)]
            return rows
        finally:
            conn.close()

    def query_for_object(self, sql, params=(), row_mapper=None):
        results = self.query_for_list(sql, params, row_mapper)
        if len(results) == 0:
            raise RuntimeError('Expected one row but got none')
        if len(results) > 1:
            raise RuntimeError(f'Expected one row but got {len(results)}')
        return results[0]

    def update(self, sql, params=()):
        conn = self._data_source.get_connection()
        try:
            pstmt = conn.prepare_statement(sql)
            for i, v in enumerate(params, 1):
                pstmt.set_parameter(i, v)
            count = pstmt.execute_update()
            conn.commit()
            return count
        finally:
            conn.close()

    def execute(self, sql):
        conn = self._data_source.get_connection()
        try:
            stmt = conn.create_statement()
            stmt.execute(sql)
            conn.commit()
        finally:
            conn.close()
