import psycopg2
from .DbCon.dbconfig import dbconfig


class BridgeError(Exception):
    """
    Class for errors that can occure while db_bridge object
    executes query or connects to the db.

    """

    def __init__(self, proc_name, params, error):
        self.proc_name = proc_name
        self.params = params
        self.error = error

    def __str__(self):
        return "Procedure: {proc_name}\nParams: {params}\nError: {error}".format(
            proc_name=self.proc_name,
            params=self.params,
            error=self.error.__str__()
        )


class db_bridge():
    """
    Class for executing queries against DB\n
    It automaticly connects to the DB by taking connection parameters from dbconfig class\n
    It also closes connection when object is destroyed and cursor when query is executed

    Raises 
    ------
    BridgeError
    """
    connection_timeout_sec = 5

    def __init__(self):
        self.__conn = None
        self.__cur = None
        self.__init_db_connection()

    def __del__(self):
        if self.__conn:
            self.__conn.close()

    def __init_db_connection(self):
        """
        Creates DB connection and saves it to a __conn var
        """
        conn_params = dbconfig.to_dict()
        self.__conn = psycopg2.connect(user=conn_params['dbuser'],
                                       password=conn_params['dbpassword'],
                                       host=conn_params['dbhost'],
                                       port=conn_params['dbport'],
                                       database=conn_params['dbname'],
                                       connect_timeout=db_bridge.connection_timeout_sec)

    def execute_db_proc_with_params(self, proc_name, param_list=None):
        try:
            self.__cur = self.__conn.cursor()

            query = self.__query_for_invoking_db_proc(proc_name, len(param_list))
            self.__cur.execute(query, param_list)
            self.__conn.commit()

            return self.__cur.fetchall()

        except (Exception, psycopg2.Error) as error:
            raise BridgeError(proc_name, param_list, error)

        finally:
            if self.__cur:
                self.__cur.close()

    def __query_for_invoking_db_proc(self, proc_name, param_list_len):
        sql = "SELECT *\nFROM %s(" % proc_name
        for i in range(param_list_len):
            if i > 0:
                sql = sql + ", "
            sql = sql + '%s'
        sql = sql + ")"

        return sql
