import os
import traceback

from flask import Flask, render_template, url_for, redirect
from sqlalchemy.exc import ProgrammingError

from app.database import db_session
from app.models import CMXServer

app = Flask(__name__, static_url_path='/static')

# Configurations
app.config.from_object(os.environ['APP_SETTINGS'])


from app.mod_cmx_server.controller import mod_cmx_server as cmx_server_module
# Register blueprint(s)
app.register_blueprint(cmx_server_module)
# app.register_blueprint(xyz_module)
# ..

@app.route('/')
def index():
    return render_template('home/index.html')


@app.route('/error')
def error():
    return render_template('base/error.html')

@app.before_first_request
def before_first_request():
    print ("FIRST REQUEST RECEIVED")
    try:
        db_session.query(CMXServer).first()
    except ProgrammingError as e:
        if str(e).__contains__("does not exist"):
            # DB Tables have not been created
            from app.database import init_db
            database.init_db()


        else:
            # Unknown error
            raise Exception(e)
    except Exception as e:
        traceback.print_exc()

# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return render_template('_base/404.html'), 404


@app.teardown_appcontext
def shutdown_session(exception=None):
    try:
        db_session.commit()
    except:
        traceback.print_exc()
        print ("Error commiting db_session")

    try:
        db_session.remove()
        traceback.print_exc()
    except:
        print ("Error removing the db_session")



if __name__ == '__main__':
    app.run()
