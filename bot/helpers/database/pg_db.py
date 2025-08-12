import time
import psycopg2
import psycopg2.extras

from bot.logger import LOGGER

class DataBaseHandle:
    _active_connections = []
    _connection_users = []

    def __init__(self, dburl: str = None) -> None:
        """Load the DB URL if available
        Args:
            dburl (str, optional): The database URI to connect to. Defaults to None.
        """

        self._dburl = dburl

        if isinstance(self._dburl, bool):
            self._block = True
        else:
            self._block = False

        if self._block:
            return

        if self._active_connections:
            self._conn = self._active_connections[0]
            self._connection_users.append(1)
        else:
            LOGGER.info("DATABASE : Established Connection")
            self._conn = psycopg2.connect(
                self._dburl,
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
                application_name="apple-bot",
            )
            self._connection_users.append(1)
            self._active_connections.append(self._conn)

    def scur(self, dictcur: bool = False) -> psycopg2.extensions.cursor:
        """Starts a new cursor for the connection.
        Args:
            dictcur (bool, optional): If this is true the returned cursor
            is in dict form insted of list. Defaults to False.
        Returns:
            psycopg2.extensions.cursor: A cursor to execute sql queries.
        """

        cur = None
        for i in range(0, 5):
            try:
                if dictcur:
                    cur = self._conn.cursor(
                        cursor_factory=psycopg2.extras.DictCursor
                    )
                else:
                    cur = self._conn.cursor()
                # Lightweight health check to proactively detect dropped connections
                try:
                    cur.execute("SELECT 1")
                except psycopg2.Error as ping_err:
                    LOGGER.debug(
                        f"Cursor health check failed (attempt {i+1}), reconnecting. {ping_err}"
                    )
                    try:
                        cur.close()
                    except Exception:
                        pass
                    self.re_establish()
                    continue
                break

            except psycopg2.Error as e:
                LOGGER.debug(
                    f"Attempting to Re-establish the connection to server {i} times. {e}"
                )
                self.re_establish()

        return cur

    def re_establish(self) -> None:
        """Re tries to connect to the database if in any case it disconnects.
        """

        try:
            LOGGER.debug("Re-establishing database connection...")
            new_conn = psycopg2.connect(
                self._dburl,
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
                application_name="apple-bot",
            )
            self._conn = new_conn
            if self._active_connections:
                self._active_connections[0] = new_conn
            else:
                self._active_connections.append(new_conn)
            LOGGER.debug("Re-establish Success.")
        except Exception:
            time.sleep(1)  # Blocking call ... this stage is panic.

    def ccur(self, cursor: psycopg2.extensions.cursor) -> None:
        """Closes the cursor that is passed to it.
        Args:
            cursor (psycopg2.extensions.cursor): The cursor that needs to be closed.
        """

        if cursor is not None:
            self._conn.commit()
            cursor.close()

    def __del__(self):
        """Close connection so that it will not overload the database server..
        """

        if self._block:
            return
        self._connection_users.pop()

        if not self._connection_users:
            self._conn.close()
