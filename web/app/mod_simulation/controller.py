from flask import Blueprint, request, render_template, session, redirect

import app
from app.database import db_session
from app.mod_user.models import RegisteredUser
from app.models import Floor

mod_simulation = Blueprint('mod_simulation', __name__, url_prefix='/simulation')


@mod_simulation.route('/', methods=['GET'])
def add():
    users = db_session.query(RegisteredUser).all()
    floors = db_session.query(Floor).all()
    output = render_template("simulation/add.html", floors=floors, users=users)
    return output
