import traceback
import json
from flask import Blueprint, render_template, redirect, request, url_for

from app.mod_api import controller as api_module
from app import get_controller, get_api_cmx

mod_monitor = Blueprint('mod_monitor', __name__, url_prefix='/monitor')


@mod_monitor.route('/overview/')
def overview():
    data = {'error': None,
            'items': None
            }
    return render_template('monitor/show/overview_show.html', data=data)


@mod_monitor.route('/device/select', methods=['GET', 'POST'])
def device_select():
    data = api_module.get_devices_and_users(order_by=('location', 'last_modified', 'DESC'))

    if request.method == 'GET':
        output = render_template('monitor/select/device_select.html', data=map(json.dumps, data))
    else:
        mac_address = request.form["mac"]
        url = url_for('.device_show', mac=mac_address)
        output = redirect(url)
    return output


@mod_monitor.route('/device/<mac>')
def device_show(mac):
    data = {'error': None,
            'items': None
            }
    try:
        items = api_module.get_device_location(mac, use_asynchronous_data=True)

        data['items'] = items
    except Exception as e:
        data = {'error': True,
                'error_message': str(e)
                }
        traceback.print_exc()
    return render_template('monitor/show/device_show.html', data=data, mac_address=mac)


@mod_monitor.route('/hierarchy/select', methods=['GET', 'POST'])
def hierarchy_select():
    if request.method == 'GET':
        ctrl = get_controller()
        data = ctrl.get_hierarchies()
        output = render_template('monitor/select/device_select.html', data=map(json.dumps, data))
    else:
        hierarchy = request.form["hierarchy"]
        url = url_for('.hierarchy_show', hierarchy=hierarchy)
        output = redirect(url)

    return output


@mod_monitor.route('/hierarchy/<hierarchy>')
def hierarchy_show(hierarchy):
    data = api_module.get_devices_and_users(hierarchy=hierarchy, order_by=('location', 'last_modified', 'DESC'))
    output = render_template('monitor/show/device_show.html', data=map(json.dumps, data))
    return output