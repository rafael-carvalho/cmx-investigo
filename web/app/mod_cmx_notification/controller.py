"""
Logic of notification processing:

1) Add each and every notification that arrives to its respective database table;
2) Every time a view requests an update through an ajax request (~ 5 seconds), check the DeviceTrackingStatus table to see if the data is outdated;
3) If it is outdated, update each MAC address found on table DeviceTrackingHistory with its latest location (disregard absence notifications);
4) Filter all the notifications each MAC Address and put the latest one on the DeviceTracking table, which will have its location and last updated time. If there' a more recent absence notification to that device, do not put it on this table;
5) Clear notifications tables;
6) Return the data to the views, filtered by hierarchy, mac_address or all (depending on the view request).
"""
import traceback, json
from flask import Blueprint, request, session
from app.database import db_session
from app.mod_cmx_notification.models import CMXNotificationAbsence, CMXNotification

mod_cmx_notification = Blueprint('mod_cmx_notification', __name__, url_prefix='/cmx_notification')


@mod_cmx_notification.route('/', methods=['POST'])
def add():
    # https://developer.cisco.com/site/cmx-mobility-services/learn/tutorials/node-js-listener/
    # https://msesandbox.cisco.com:8081/manage/#notifications
    output_text = "Empty"
    try:
        if request.data:
            # It means the request was originated from CMX
            request_json = request.json
            notifications = request_json["notifications"]
        else:
            # It means the request was originated from the App from the simulation page
            messages = session['messages']
            messages = json.loads(messages)
            notifications = messages['notifications']

        for notification in notifications:
            mac_address = notification["deviceId"]
            notification_type = notification["notificationType"]

            last_seen = notification["lastSeen"]
            subscription_name = notification["subscriptionName"]
            floor_id = notification["floorId"]
            event_id = notification["eventId"]
            timestamp = notification["timestamp"]
            band = notification["band"]
            entity = notification['entity']
            location_map_hierarchy = notification['locationMapHierarchy']
            location_x  = notification['locationCoordinate']['x']
            location_y = notification['locationCoordinate']['y']
            location_z = notification['locationCoordinate']['z']
            location_unit = notification['locationCoordinate']['unit']
            # Not every notification has all fields
            ap_mac_address = get_value_or_default(notification, "apMacAddress")

            ssid = get_value_or_default(notification, "ssid")
            confidence_factor = get_value_or_default(notification, "confidence_factor")

            db_object = None

            if notification_type == 'absence':
                absence_duration_minutes = get_value_or_default(notification, "absenceDurationInMinutes")
                db_object = CMXNotificationAbsence(mac_address, notification_type, subscription_name, timestamp, last_seen, event_id, floor_id, band, entity, location_map_hierarchy, location_x, location_y, location_z, location_unit, ssid, ap_mac_address, absence_duration_minutes)
            else:
                db_object = CMXNotification(mac_address, notification_type, subscription_name, timestamp,
                                                   last_seen, event_id, floor_id, band, entity, location_map_hierarchy,
                                                   location_x, location_y, location_z, location_unit, ssid, ap_mac_address)

            db_session.add(db_object)

            output_text = "{} notification for {}".format(notification_type, mac_address)


    except:
        db_session.rollback()
        print ("Error handling CMX Notification!")
        traceback.print_exc()
        output_text = "Error!"

    finally:
        print (output_text)

    return output_text

def get_value_or_default(dictionary, key, default_value=None):
    output = default_value
    try:
        output = dictionary[key]
    except KeyError:
        pass
    return output