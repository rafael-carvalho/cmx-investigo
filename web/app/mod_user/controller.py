import traceback
import json
from flask import Blueprint, render_template, redirect, request, url_for, Response

from app.database import db_session
from app.mod_user.models import RegisteredUser

mod_user = Blueprint('mod_user', __name__, url_prefix='/user')


@mod_user.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'GET':
        output = render_template("user/add.html")
    else:
        output = {
            'error': None,
            'error_message': None,
            'redirect_url': None,
        }
        try:
            if request.json:
                form_data = request.json
            else:
                form_data = request.form
            name = form_data["user_name"]
            phone = form_data["user_phone"]
            mac_address = form_data["user_mac_address"]
            user = RegisteredUser(name, mac_address, phone)
            db_session.add(user)
            db_session.commit()
            output['redirect_url'] = url_for('mod_user.show')
        except Exception as e:
            output['error'] = True
            output['error_message'] = str(e)
            db_session.rollback()
        finally:
            output = Response(json.dumps(output), mimetype='application/json')

    return output


@mod_user.route('/')
@mod_user.route('/show')
def show():
    try:
        users = db_session.query(RegisteredUser).all()
        return render_template("user/list.html", object=users)

    except:
        traceback.print_exc()
        return "No response"


@mod_user.route('/details/<id>')
def details(id):
    user = db_session.query(RegisteredUser).filter(RegisteredUser.id == id).first()
    return render_template("user/details.html", object=user)


@mod_user.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    user = db_session.query(RegisteredUser).filter(RegisteredUser.id == id).first()
    if not user:
        output = redirect(url_for('error', message='User with id = {} does not exist'.format(id)))
    else:
        if request.method == 'GET':
            output = render_template("user/edit.html", object=user)
        else:
            output = {
                'error': None,
                'error_message': None,
                'redirect_url': None,
            }
            try:
                if request.json:
                    form_data = request.json
                else:
                    form_data = request.form
                name = form_data["user_name"]
                phone = form_data["user_phone"]
                mac_address = form_data["user_mac_address"]
                user.name = name
                user.phone = phone
                user.mac_address = mac_address

                db_session.commit()
                output['redirect_url'] = url_for('mod_user.show')
            except Exception as e:
                output['error'] = True
                output['error_message'] = str(e)
                db_session.rollback()
            finally:
                output = Response(json.dumps(output), mimetype='application/json')
    return output


@mod_user.route('/delete/<id>', methods=['GET', 'POST'])
def delete(id):
    user = db_session.query(RegisteredUser).filter(RegisteredUser.id == id).first()
    if not user:
        output = redirect(url_for('error', message='User with id = {} does not exist'.format(id)))
    else:
        if request.method == 'GET':
            output = render_template("user/delete.html", object=user)
        else:
            db_session.delete(user)
            output = redirect(url_for('mod_user.show'))
    return output
