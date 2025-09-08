import os
from dotenv import load_dotenv

load_dotenv()

NURSACE_DB_HOST = os.environ.get("NURSACE_POSTGRESQL_HOST")
NURSACE_DB_PORT = os.environ.get("NURSACE_POSTGRESQL_PORT")
NURSACE_DB_NAME = os.environ.get("NURSACE_POSTGRESQL_DBNAME")
NURSACE_DB_USER = os.environ.get("NURSACE_POSTGRESQL_USER")
NURSACE_DB_PASS = os.environ.get("NURSACE_POSTGRESQL_PASSWORD")

MARELLA_DB_HOST = os.environ.get("MARELLA_POSTGRESQL_HOST")
MARELLA_DB_PORT = os.environ.get("MARELLA_POSTGRESQL_PORT")
MARELLA_DB_NAME = os.environ.get("MARELLA_POSTGRESQL_DBNAME")
MARELLA_DB_USER = os.environ.get("MARELLA_POSTGRESQL_USER")
MARELLA_DB_PASS = os.environ.get("MARELLA_POSTGRESQL_PASSWORD")

# Режим работы: dev или prod
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev").lower()
IS_DEV = ENVIRONMENT == "dev"
