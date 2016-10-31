from flask import Blueprint, request, render_template, session, redirect

import app
from app.database import db_session
from app.mod_user.models import RegisteredUser
from app.models import Floor

mod_error = Blueprint('mod_error', __name__, url_prefix='/error')


@mod_error.route('/<message>', methods=['GET'])
def home(message=None):
    return render_template('_base/error.html', message=message)
