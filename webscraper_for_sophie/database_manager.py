# import default packages
import logging
import time
# import installed packages
import environs
import mysql.connector
from mysql.connector import errorcode
# import project modules
from webscraper_for_sophie.items import CondoItem


env = environs.Env()
USER = env("MYSQL_USER")
PASSWORD = env("MYSQL_PASSWORD")
DATABASE = env("MYSQL_DATABASE")
TABLENAME = env("MYSQL_TABLENAME")
HOST = "192.168.1.52"  # server hosted DB
PORT = "3307"

# Settings for connection error handling
NUM_ATTEMPTS = 30
DELAY_BTW_ATTEMPTS = 1     # in seconds
RETRY_MSG = ("Waiting for MySQL container to start gracefully " +
             "(Attempt {} of {}) failed")


class DatabaseManager():
    """
    Simplies our database operations
    """

    def connect(self):
        """ Connect to the database """
        for attempt_no in range(1, NUM_ATTEMPTS+1):
            try:
                self.connection = mysql.connector.connect(host=HOST,
                                                          port=PORT,
                                                          database=DATABASE,
                                                          user=USER,
                                                          password=PASSWORD)
                self.cursor = self.connection.cursor()
                logging.debug("Database connection opened")
                return
            except mysql.connector.Error as err:
                logging.debug(RETRY_MSG.format(attempt_no, NUM_ATTEMPTS))
                if attempt_no < NUM_ATTEMPTS:
                    time.sleep(DELAY_BTW_ATTEMPTS)
                else:
                    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                        logging.error(
                            "Something is wrong with your user name or password")
                    elif err.errno == errorcode.ER_BAD_DB_ERROR:
                        logging.error("Database does not exist")
                    else:
                        logging.error(err)

    def close(self):
        """ Close the database connection """
        self.connection.close()
        logging.debug("Database connection closed")

    def is_connected(self):
        """ 
        Returns:
            bool: True if connected. False otherwise        
        """
        self.connection.is_connected()

    def prep_table(self):
        """ create a new table if the provided table name does not exist. """
        sql_command = "SHOW TABLES LIKE '{0}'".format(TABLENAME)
        self.cursor.execute(sql_command)
        result = self.cursor.fetchone()  # fetch will return a python tuple
        if result is None:
            logging.debug("Database table does not exist")

            # create table
            sql_command = """
            CREATE TABLE {0} ( 
            id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
            willhaben_code VARCHAR(10) COLLATE utf8_bin,
            postal_code VARCHAR(10) COLLATE utf8_bin,
            district VARCHAR(100) COLLATE utf8_bin,
            price INTEGER,
            commission_fee FLOAT,
            size INTEGER,
            room_count INTEGER,
            price_per_m2 FLOAT,
            discovery_date DATE,
            title TEXT COLLATE utf8_bin,
            url TEXT COLLATE utf8_bin,
            edit_date VARCHAR(100) COLLATE utf8_bin,
            address VARCHAR(100) COLLATE utf8_bin);""".format(TABLENAME)
            self.cursor.execute(sql_command)
            self.connection.commit()
            logging.debug("New database table has been created")

    def store_item(self, item):
        """ 
        Store a new item in the database

        Args:
            item: the CondoItem that should be inserted in the database.
        """

        # fill table of database with data
        sql_command = """INSERT INTO {0} 
							(id, willhaben_code, postal_code, district, price,
                            commission_fee, size, room_count, price_per_m2, 
                            discovery_date, title, url, edit_date, address)
						VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s);
						""".format(TABLENAME)

        insert_tuple = (None, item['willhaben_code'], item['postal_code'],
                        item['district'], item['price'], item['commission_fee'],
                        item['size'], item['room_count'], item['price_per_m2'],
                        item['discovery_date'], item['title'], item['url'],
                        item['edit_date'], item['address'])
        # use parameterized input to avoid SQL injection
        self.cursor.execute(sql_command, insert_tuple)
        # never forget this, if you want the changes to be saved:
        self.connection.commit()
