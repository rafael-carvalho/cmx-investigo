import traceback

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, convert_unicode=True)

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=True,
                                         bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    try:
        # import all modules here that might define models so that
        # they will be registered properly on the metadata.  Otherwise
        # you will have to import them first before calling init_db()
        import app.models
        import app.mod_cmx_notification.models

        print ("Removing all tables from database")
        Base.metadata.drop_all(bind=engine)

        print ("Adding all tables from database")
        Base.metadata.create_all(bind=engine)
        db_session.commit()

    except:
        traceback.print_exc()