from neomodel import config, db, install_all_labels

from piper.config import NEO4J_DB_URL


def db_config():
    return {
        'url': NEO4J_DB_URL
    }


def transaction_manager():
    return db.transaction


def start_db():
    pass


def config_db():
    config.DATABASE_URL = NEO4J_DB_URL
    config.ENCRYPTED_CONNECTION = False


def init_db():
    install_all_labels()

