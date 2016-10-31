import contextlib
import traceback
import json

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import scoped_session, sessionmaker

from config import Config

db_engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, convert_unicode=True)#, echo=True)

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=True,
                                         bind=db_engine))

Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    output = {
        'error': None,
        'status': 'Tables deleted and created successfully'
    }
    try:
        # import all modules here that might define models so that
        # they will be registered properly on the metadata.  Otherwise
        # you will have to import them first before calling init_db()
        import app.models
        import app.mod_cmx_notification.models
        import app.mod_user.models
        db_session.commit()
        print ("Removing all tables from database")

        with contextlib.closing(db_engine.connect()) as con:
            trans = con.begin()
            for table in reversed(Base.metadata.sorted_tables):
                try:
                    sql = 'DROP TABLE {} CASCADE;'.format(table.name)
                    db_engine.execute(sql)
                except Exception as e:
                    print (str(e))
            trans.commit()

        Base.metadata.drop_all(bind=db_engine)
        db_session.commit()
        print ("Adding all tables from database")
        Base.metadata.create_all(bind=db_engine)
        db_session.commit()

    except Exception as e:
        output = {
            'error': True,
            'status': str(e)
        }
        traceback.print_exc()

    return output


def clear_db():
    output = {
        'error': None,
        'status': 'Tables cleared successfully'
    }

    try:
        with contextlib.closing(db_engine.connect()) as con:
            trans = con.begin()
            sql = ''

            for table in reversed(Base.metadata.sorted_tables):
                sql += 'TRUNCATE {} CASCADE;'.format(table.name)

            db_engine.execute(sql)

            trans.commit()

    except Exception as e:
        output = {
            'error': True,
            'status': str(e)
        }
        traceback.print_exc()

    return output


def close_db():
    try:
        db_session.commit()
    except:
        traceback.print_exc()
        print ("Error commiting db_session")

    try:
        db_session.remove()
    except:
        traceback.print_exc()
        print ("Error removing the db_session")