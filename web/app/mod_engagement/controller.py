import json
import traceback

from flask import Blueprint, render_template, request, Response, url_for, redirect

from app import get_api_spark, get_api_tropo
from app.database import db_session
from app.mod_user.models import RegisteredUser
from app.models import Floor, EngagementTrigger, Zone

mod_engagement = Blueprint('mod_engagement', __name__, url_prefix='/engagement')


@mod_engagement.route('/', methods=['GET'])
def home():
    output = render_template("engagement/engagement_home.html")
    return output


@mod_engagement.route('/screen/select', methods=['GET', 'POST'])
def engagement_screen_select():
    if request.method == 'GET':
        floors = db_session.query(Floor).all()
        output = render_template("engagement/screen/engagement_select.html", floors=floors)
    else:
        output = redirect(url_for('.engagement_screen_show', hierarchy=request.form['hierarchy']))
    return output


@mod_engagement.route('/screen/<hierarchy>', methods=['GET'])
def engagement_screen_show(hierarchy):
    zone_name = hierarchy.split('>')[-1]
    zone = db_session.query(Zone).filter(Zone.name == zone_name).first()
    triggers = []
    for t in get_engagement_triggers_per_zone(zone.id):
        triggers.append(t.serialize())
    output = render_template("engagement/screen/engagement_show.html", hierarchy=hierarchy, triggers=triggers)
    return output


@mod_engagement.route('/trigger/', methods=['GET'])
def engagement_trigger_list():
    output = render_template("engagement/trigger/trigger_home.html")
    return output


@mod_engagement.route('/trigger/add', methods=['GET'])
def engagement_trigger_add():
    floors = db_session.query(Floor).all()
    users = db_session.query(RegisteredUser).all()
    output = render_template("engagement/trigger/trigger_add.html", users=users, floors=floors)
    return output


@mod_engagement.route('/trigger/user/add', methods=['POST'])
def engagement_trigger_user_add():
    output = {
        'error': True,
        'error_message': 'Unknown error',
        'message': None,
    }
    if request.json:
        request_json = request.json
        registered_user_id = request_json['registered_user_id']
        zone_id = request_json['zone']
        event = request_json['event']

        triggers_created = 0
        post_on_spark = 'spark_checkbox' in request_json
        if post_on_spark:
            spark_target = request_json['spark_target']
            spark_value = request_json['spark_value']
            if spark_target and spark_value:
                spark_trigger = EngagementTrigger('spark', spark_target, spark_value, event, zone_id, registered_user_id, extras=None)
                db_session.add(spark_trigger)
                triggers_created += 1

        post_on_tropo = 'tropo_checkbox' in request_json
        if post_on_tropo:
            tropo_target = request_json['tropo_target']
            tropo_platform = request_json['tropo_platform']
            tropo_value = request_json['tropo_value']
            if tropo_target and tropo_platform and tropo_value:
                tropo_trigger = EngagementTrigger('tropo', tropo_target, tropo_value, event, zone_id, registered_user_id, extras=tropo_platform)
                db_session.add(tropo_trigger)
                triggers_created += 1

        try:
            db_session.commit()
            output = {
                'error': False,
                'error_message': None,
                'message': "{} trigger(s) created".format(triggers_created)
            }
        except:
            output = {
                'error': True,
                'error_message': 'Error on trigger creation.',
                'message': None,
            }
            traceback.print_exc()
    else:
        output = {
            'error': True,
            'error_message': 'JSON data not provided on request',
            'message': None,
        }
    return Response(json.dumps(output), mimetype='application/json')


@mod_engagement.route('/trigger/user/<registered_user_id>/view', methods=['GET'])
def engagement_trigger_user_list(registered_user_id):
    # output = render_template("engagement/show.html", hierarchy=hierarchy)
    output = 'Under construction'
    return output


@mod_engagement.route('/trigger/user/fire', methods=['POST'])
def fire_user_zone_trigger():

    try:
        trigger = None
        if request.json:
            trigger = db_session.query(EngagementTrigger).filter(EngagementTrigger.id == request.json['trigger_id']).first()
        if trigger:

            user = db_session.query(RegisteredUser).filter(RegisteredUser.id == trigger.registered_user_id).first()
            zone = db_session.query(Zone).filter(Zone.id == trigger.zone_id).first()
            if user and zone:
                platform = trigger.platform
                text = trigger.value
                text = replace_user_info_on_trigger_text(text, user)
                text = replace_zone_information(text, zone)
                response = None
                if trigger.platform == 'spark':
                    # do action
                    room_id = trigger.target
                    response = get_api_spark().messages.create(roomId=room_id, text=text)
                elif trigger.platform == 'tropo':
                    number = trigger.target
                    number = replace_user_info_on_trigger_text(number, user)
                    tropo_platform = trigger.extras
                    response = get_api_tropo().triggerTropoWithMessageAndNumber(text, number, voice="dave", type=tropo_platform)

                ok = response.status_code == 200

                if ok:
                    output = {
                        'error': False,
                        'error_message': None,
                        'message': 'Successfully posted on {}'.format(platform),
                    }
                else:
                    output = {
                        'error': True,
                        'error_message': 'Error when trying to post to on {}'.format(platform),
                        'message': None,
                    }
            else:
                output = {
                    'error': True,
                    'error_message': 'User or Zone not found ids = {} / {}'.format(trigger.registered_user_id, trigger.zone_id),
                    'message': None,
                }
        else:
            output = {
                'error': True,
                'error_message': 'Trigger id not provided as json.',
                'message': None,
            }
    except Exception as e:
        output = {
            'error': True,
            'error_message': 'Unknown error\n{}'.format(str(e)),
            'message': None,
        }
        traceback.print_exc()

    return Response(json.dumps(output), mimetype='application/json')


def replace_user_info_on_trigger_text(text, user):
    text = text.replace('{user.name}', str(user.name))
    text = text.replace('{user.phone}', str(user.phone))
    text = text.replace('{user.id}', str(user.id))
    return text


def replace_zone_information(text, zone):
    text = text.replace('{zone.name}', str(zone.name))
    text = text.replace('{zone.id}', str(zone.id))
    text = text.replace('{zone.floor}', str(zone.floor.name))
    return text



def get_engagement_triggers_per_zone(zone_id):
    output = []
    triggers = db_session.query(EngagementTrigger).filter(EngagementTrigger.zone_id == zone_id).all()

    for t in triggers:
        output.append(t)

    return output
