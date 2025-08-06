import psycopg2
import datetime
import psycopg2.extras
from .pg_db import DataBaseHandle
from config import Config

class BotSettings(DataBaseHandle):
    def __init__(self, dburl=None):
        if dburl is None:
            dburl = Config.DATABASE_URL
        super().__init__(dburl)

        settings_schema = """CREATE TABLE IF NOT EXISTS bot_settings (
            id SERIAL PRIMARY KEY NOT NULL,
            var_name VARCHAR(50) NOT NULL UNIQUE,
            var_value VARCHAR(2000) DEFAULT NULL,
            vtype VARCHAR(20) DEFAULT NULL,
            blob_val BYTEA DEFAULT NULL,
            date_changed TIMESTAMP NOT NULL
        )"""

        cur = self.scur()
        try:
            cur.execute(settings_schema)
        except psycopg2.errors.UniqueViolation:
            pass

        self._conn.commit()
        self.ccur(cur)

    def set_variable(self, var_name, var_value, update_blob=False, blob_val=None):
        vtype = "str"
        if isinstance(var_value, bool):
            vtype = "bool"
        elif isinstance(var_value, int):
            vtype = "int"

        if update_blob:
            vtype = "blob"

        sql = "SELECT * FROM bot_settings WHERE var_name=%s"
        cur = self.scur()

        cur.execute(sql, (var_name,))
        if cur.rowcount > 0:
            if not update_blob:
                sql = "UPDATE bot_settings SET var_value=%s , vtype=%s WHERE var_name=%s"
            else:
                sql = "UPDATE bot_settings SET blob_val=%s , vtype=%s WHERE var_name=%s"
                var_value = blob_val

            cur.execute(sql, (var_value, vtype, var_name))
        else:
            if not update_blob:
                sql = "INSERT INTO bot_settings(var_name,var_value,date_changed,vtype) VALUES(%s,%s,%s,%s)"
            else:
                sql = "INSERT INTO bot_settings(var_name,blob_val,date_changed,vtype) VALUES(%s,%s,%s,%s)"
                var_value = blob_val

            cur.execute(sql, (var_name, var_value, datetime.datetime.now(), vtype))

        self.ccur(cur)

    def get_variable(self, var_name):
        sql = "SELECT * FROM bot_settings WHERE var_name=%s"
        cur = self.scur()

        cur.execute(sql, (var_name,))
        if cur.rowcount > 0:
            row = cur.fetchone()
            vtype = row[3]
            val = row[2]
            if vtype == "int":
                val = int(row[2])
            elif vtype == "str":
                val = str(row[2])
            elif vtype == "bool":
                if row[2] == "true":
                    val = True
                else:
                    val = False

            return val, row[4]
        else:
            return None, None

        self.ccur(cur)

    def __del__(self):
        super().__del__()

class DownloadHistory(DataBaseHandle):
    def __init__(self, dburl=None):
        if dburl is None:
            dburl = Config.DATABASE_URL
        super().__init__(dburl)
        
        # Create download history table
        schema = """
        CREATE TABLE IF NOT EXISTS download_history (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            provider VARCHAR(20) NOT NULL,
            content_type VARCHAR(10) NOT NULL,
            content_id VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            artist VARCHAR(255) NOT NULL,
            quality VARCHAR(20),
            download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_user_downloads ON download_history(user_id);
        """
        cur = self.scur()
        cur.execute(schema)
        self._conn.commit()
        self.ccur(cur)
    
    def record_download(self, user_id, provider, content_type, content_id, title, artist, quality):
        sql = """
        INSERT INTO download_history 
        (user_id, provider, content_type, content_id, title, artist, quality) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur = self.scur()
        cur.execute(sql, (user_id, provider, content_type, content_id, title, artist, quality))
        self._conn.commit()
        self.ccur(cur)
    
    def get_user_history(self, user_id, limit=10):
        sql = "SELECT * FROM download_history WHERE user_id = %s ORDER BY download_time DESC LIMIT %s"
        cur = self.scur(dictcur=True)
        cur.execute(sql, (user_id, limit))
        results = cur.fetchall()
        self.ccur(cur)
        return results

# Initialize database handlers
set_db = BotSettings()
download_history = DownloadHistory()
