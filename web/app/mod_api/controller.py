import traceback, json
from flask import Blueprint, request
from app.database import db_session

mod_api = Blueprint('mod_cmx_api', __name__, url_prefix='/api')

@mod_api.route('/hierarchy/<hierarchy>')
def clients_hierarchy(hierarchy):
    output = {}

    return json.dumps(output)


@mod_api.route('/overview')
def overview():
    output = {}

    return json.dumps(output)


@mod_api.route('/client/<mac_address>')
def client(mac_address):
    output = {}
    return json.dumps(output)


@mod_api.route('/engagement/<hierarchy>/<mac_address>')
@mod_api.route('/engagement/<hierarchy>')
def client(hierarchy, mac_address=None):
    output = {}

    return json.dumps(output)

"""
'error' : Message or None,

'hierarchy' : {

    'name' : hierarchy.name,
    'verticalName' : getVertical(hierarchy, vertical, language),
    'mapInfo' : {
        'map_resource' : url_for (hierarchy.map_info ...),
        width : ...,
    },
    unknownDevices : [
        {
            'macAddress' : mac_address,
            'lastSeen' : last_seen,
            "geoCoordinate": {
              "latitude": -999,
              "longitude": -999,
              "unit": "DEGREES"
            },
            locationCoordinate : {
                'x' : x,
                'y' : y,
                'z' : z,
                'unit' : default="FEET"
            }

        },
    ],

    users : [
        {
            'macAddress' : mac_address,
            'lastSeen' : last_seen,
            "geoCoordinate": {
              "latitude": -999,
              "longitude": -999,
              "unit": "DEGREES"
            },
            locationCoordinate : {
                'x' : x,
                'y' : y,
                'z' : z,
                'unit' : default="FEET"
            }
            'name' : user.name,
            'phoneNumber' : user.phone_number,
            'extra' : user.extra #external API customization
        },
    ],
}
"""