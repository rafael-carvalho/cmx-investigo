# Import flask dependencies
import traceback

from flask import Blueprint, render_template, request, url_for, redirect

from app.database import db_session
from app.models import CMXServer

mod_device = Blueprint('mod_device', __name__, url_prefix='/device')

@mod_device.route('/')
@mod_device.route('/show')
def show():
    try:
        return render_template("device/list.html", object=servers)
    except:
        traceback.print_exc()
        return "No response"

@mod_device.route('/details/<mac_address>')
def details(mac_address):
    return render_template("device/details.html", object=server)