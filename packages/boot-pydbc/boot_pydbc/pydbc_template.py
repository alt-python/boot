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

    def query_for_map(self, sql, params=()):
        """Execute a query expecting exactly one row, returned as a dict."""
        return self.query_for_object(sql, params)

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

    def batch_update(self, sql, params_list):
        """Execute *sql* for each params tuple in *params_list*.

        All rows share a single connection; each statement is executed
        individually. Returns a list of affected row counts.
        """
        conn = self._data_source.get_connection()
        try:
            counts = []
            for params in params_list:
                pstmt = conn.prepare_statement(sql)
                for i, v in enumerate(params, 1):
                    pstmt.set_parameter(i, v)
                counts.append(pstmt.execute_update())
            conn.commit()
            return counts
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

    def execute_in_transaction(self, callback):
        """Execute *callback(tx)* inside a transaction.

        *callback* receives a :class:`TransactionTemplate` bound to the
        connection.  The transaction is committed on success and rolled back
        on any exception.  The callback return value is forwarded to the
        caller.
        """
        conn = self._data_source.get_connection()
        conn.set_auto_commit(False)
        tx = TransactionTemplate(conn)
        try:
            result = callback(tx)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class TransactionTemplate:
    """PydbcTemplate-like API bound to a single open connection.

    Used inside :meth:`PydbcTemplate.execute_in_transaction` callbacks.
    All operations share the connection; the caller must not close it.
    """

    def __init__(self, connection):
        self._conn = connection

    def query_for_list(self, sql, params=(), row_mapper=None):
        pstmt = self._conn.prepare_statement(sql)
        for i, v in enumerate(params, 1):
            pstmt.set_parameter(i, v)
        rs = pstmt.execute_query()
        rows = rs.get_rows()
        rs.close()
        if row_mapper:
            return [row_mapper(row, i) for i, row in enumerate(rows)]
        return rows

    def query_for_object(self, sql, params=(), row_mapper=None):
        results = self.query_for_list(sql, params, row_mapper)
        if len(results) == 0:
            raise RuntimeError('Expected one row but got none')
        if len(results) > 1:
            raise RuntimeError(f'Expected one row but got {len(results)}')
        return results[0]

    def query_for_map(self, sql, params=()):
        return self.query_for_object(sql, params)

    def update(self, sql, params=()):
        pstmt = self._conn.prepare_statement(sql)
        for i, v in enumerate(params, 1):
            pstmt.set_parameter(i, v)
        return pstmt.execute_update()

    def batch_update(self, sql, params_list):
        counts = []
        for params in params_list:
            pstmt = self._conn.prepare_statement(sql)
            for i, v in enumerate(params, 1):
                pstmt.set_parameter(i, v)
            counts.append(pstmt.execute_update())
        return counts

    def execute(self, sql):
        stmt = self._conn.create_statement()
        stmt.execute(sql)
