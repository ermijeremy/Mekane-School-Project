import os
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     os.getenv("DB_PORT",     "5432"),
    "dbname":   os.getenv("DB_NAME",     "school_db"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}


HASHED_PASSWORD = "$2b$12$KIX9d3lB3FJn7w0pY9k3CO5aZlGmT/oPJfZkE6H4mGqVMNFUJ5Rai"

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "db/schema.sql")

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTE = os.getenv("JWT_EXPIRE_MINUTE", 1440)
