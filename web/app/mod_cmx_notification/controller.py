import json
import traceback

from flask import Blueprint, request, session, Response
from app.database import db_session
from app.mod_cmx_notification.models import CMXNotification

mod_cmx_notification = Blueprint('mod_cmx_notification', __name__, url_prefix='/cmx')


@mod_cmx_notification.route('/', methods=['POST'])
def add():
    # https://developer.cisco.com/site/cmx-mobility-services/learn/tutorials/node-js-listener/
    # https://msesandbox.cisco.com:8081/manage/#notifications
    output = {
        'error': True,
        'error_message': 'Unknown error',
        'message': None,
    }
    try:
        if request.json:
            request_json = request.json
            notifications = request_json["notifications"]
            for notification in notifications:
                mac_address = notification["deviceId"]
                notification_type = notification["notificationType"]

                last_seen = notification["lastSeen"]
                subscription_name = notification["subscriptionName"]
                floor_id = notification["floorId"]
                event_id = notification["eventId"]
                timestamp = notification["timestamp"]
                location_map_hierarchy = notification['locationMapHierarchy']
                location_x = notification['locationCoordinate']['x']
                location_y = notification['locationCoordinate']['y']
                location_z = notification['locationCoordinate']['z']
                location_unit = notification['locationCoordinate']['unit']
                # Not every notification has all fields
                entity = get_value_or_default(notification, 'entity')
                band = get_value_or_default(notification, "band")
                ap_mac_address = get_value_or_default(notification, "apMacAddress")

                ssid = get_value_or_default(notification, "ssid")
                confidence_factor = get_value_or_default(notification, "confidence_factor")

                absence_duration_minutes = get_value_or_default(notification, "absenceDurationInMinutes")

                db_object = CMXNotification(mac_address, notification_type, subscription_name, timestamp, confidence_factor, last_seen, event_id, floor_id, band, entity, location_map_hierarchy, location_x, location_y, location_z, location_unit, ssid, ap_mac_address, absence_duration_minutes)

                db_session.merge(db_object)
                output['error'] = False
                output['message'] = "{} notification for {}".format(notification_type, mac_address)
                output['error_message'] = None
        else:
            output['error'] = True
            output['error_message'] = 'JSON data not provided on request'
    except Exception as e:
        db_session.rollback()
        print ("Error handling CMX Notification!")
        traceback.print_exc()
        output['error_message'] = str(e)
        output['error'] = True

    finally:
        return Response(json.dumps(output), mimetype='application/json')


def get_value_or_default(dictionary, key, default_value=None):
    output = default_value
    try:
        output = dictionary[key]
    except KeyError:
        pass
    return output
