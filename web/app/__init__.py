import os
import json
import traceback

from flask import Flask, render_template, Response, request, redirect, url_for
from sqlalchemy.exc import ProgrammingError

from app.database import db_session
from externalapis.CMXAPICaller import CMXAPICaller
from ciscosparkapi import CiscoSparkAPI
from externalapis.TropoAPICaller import TropoAPICaller

app = Flask(__name__)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))   # refers to application_top

# Configurations
app.config.from_object(os.environ['APP_SETTINGS'])


def get_api_cmx(cmx_server=None):
    if not cmx_server:
        cmx_server = get_controller()

    return CMXAPICaller(cmx_server.name, cmx_server.url, cmx_server.username, cmx_server.password)


def get_api_spark():
    return CiscoSparkAPI(access_token=app.config['SPARK_TOKEN'])


def get_api_tropo():
    return TropoAPICaller(app.config['TROPO_API_KEY_VOICE'], app.config['TROPO_API_KEY_TEXT'])


def get_notification_sms_phone_number():
    return app.config['NOTIFICATION_SMS_PHONE_NUMBER']


def get_default_room_id():
    return app.config['SPARK_DEFAULT_ROOM_ID']




def get_controller():
    from app.models import CMXServer
    db_controller = db_session.query(CMXServer).filter(CMXServer.active).first()
    return db_controller


from app.models import CMXServer, DeviceLocation, DeviceLocationHistory, CMXSystem, Campus
from app.mod_cmx_server.controller import mod_cmx_server as cmx_server_mod
from app.mod_cmx_notification.controller import mod_cmx_notification as cmx_notification_mod
from app.mod_api.controller import mod_api as api_mod
from app.mod_monitor.controller import mod_monitor as monitor_mod
from app.mod_user.controller import mod_user as user_mod
from app.mod_simulation.controller import mod_simulation as simulation_mod
from app.mod_engagement.controller import mod_engagement as engagement_mod
from app.mod_error.controller import mod_error as error_mod
from app.mod_spark.controller import mod_spark as spark_mod

from app.mod_api import controller as api_controller

# Register blueprint(s)
app.register_blueprint(cmx_server_mod)
app.register_blueprint(api_mod)
app.register_blueprint(cmx_notification_mod)
app.register_blueprint(monitor_mod)
app.register_blueprint(user_mod)
app.register_blueprint(simulation_mod)
app.register_blueprint(engagement_mod)
app.register_blueprint(error_mod)
app.register_blueprint(spark_mod)

# app.register_blueprint(xyz_module)
# ..


@app.route('/')
def index():
    return render_template('home/index.html')


@app.route('/clear_db')
@app.route('/clear')
def clear():
    return Response(json.dumps(invoke_db_clear()), mimetype='application/json')


@app.route('/migrate')
def migrate():
    return Response(json.dumps(invoke_db_migration()), mimetype='application/json')


@app.before_first_request
def before_first_request():
    print ("FIRST REQUEST RECEIVED")
    try:
        db_session.query(CMXServer).first()
    except ProgrammingError as e:
        if str(e).__contains__("does not exist"):
            # DB Tables have not been created
            invoke_db_migration()
        else:
            # Unknown error
            raise Exception(e)
    except Exception as e:
        traceback.print_exc()


@app.before_request
def before_request():
    bp = request.blueprint
    # Exempting requests on the root '/something'. i.e. bp = None
    if bp and bp not in [cmx_notification_mod.name, user_mod.name, api_mod.name, error_mod.name, cmx_server_mod.name]:
        if get_controller() is None:
            return redirect(url_for('mod_error.home', message='You need to set a server'))


def invoke_db_migration():
    from app.database import init_db
    return init_db()


def invoke_db_clear():
    from app.database import clear_db
    return clear_db()


def invoke_db_close():
    from app.database import close_db
    return close_db()


# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return redirect(url_for('mod_error.home', message=404))


@app.teardown_appcontext
def shutdown_session(exception=None):
    if api_controller.too_many_notifications_rows():
        api_controller.update_tables()

    invoke_db_close()


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
    #app.run()
