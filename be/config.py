CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     os.getenv("DB_PORT",     "5432"),
    "dbname":   os.getenv("DB_NAME",     "school_db"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}


HASHED_PASSWORD = "$2b$12$KIX9d3lB3FJn7w0pY9k3CO5aZlGmT/oPJfZkE6H4mGqVMNFUJ5Rai"

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")
