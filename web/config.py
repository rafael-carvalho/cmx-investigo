import os


class Config(object):
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DEBUG = False
    SECRET_KEY = os.environ['SECRET_KEY']
    DB_NAME = os.environ['DB_NAME']
    DB_USER = os.environ['DB_USER']
    DB_PASS = os.environ['DB_PASS']
    DB_SERVICE = os.environ['DB_SERVICE']
    DB_PORT = os.environ['DB_PORT']
    SQLALCHEMY_DATABASE_URI = 'postgresql://{0}:{1}@{2}:{3}/{4}'.format(
        DB_USER, DB_PASS, DB_SERVICE, DB_PORT, DB_NAME
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    TROPO_API_KEY_TEXT = os.environ.get('TROPO_API_KEY_TEXT', "TEXT TOKEN NOT PROVIDED")
    TROPO_API_KEY_VOICE = os.environ.get('TROPO_API_KEY_VOICE', "VOICE TOKEN NOT PROVIDED")
    SPARK_TOKEN = os.environ.get('SPARK_TOKEN', "TOKEN-NOT-PROVIDED")
    ON_CISCO_NETWORK = os.environ.get('ON_CISCO_NETWORK', False)

    # Application threads. A common general assumption is
    # using 2 per available processor cores - to handle
    # incoming requests using one and performing background
    # operations using the other.
    THREADS_PER_PAGE = 2


class ProductionConfig(Config):
    DEBUG = False


class StagingConfig(Config):
    DEVELOPMENT = True
    DEBUG = True


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
