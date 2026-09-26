import os

# All values may be overridden through the environment (the installer ships
# /etc/ibsng/ibsng.env for this); defaults preserve the historic behaviour.
DB_HOST = os.environ.get("IBS_DB_HOST")  # None => local unix socket
DB_PORT = int(os.environ.get("IBS_DB_PORT", "5432"))
DB_USERNAME = os.environ.get("IBS_DB_USERNAME", "ibs")
DB_PASSWORD = os.environ.get("IBS_DB_PASSWORD", "ibsdbpass")
