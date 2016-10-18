# Import flask dependencies
import traceback

from flask import Blueprint, render_template, request, url_for, redirect

from app.database import db_session
from app.models import CMXServer

mod_cmx_server = Blueprint('mod_cmx_server', __name__, url_prefix='/cmx_server')

@mod_cmx_server.route('/')
@mod_cmx_server.route('/show')
def show():

    try:
        servers = db_session.query(CMXServer).all()
        return render_template("cmx_server/list.html", object=servers)

    except:
        traceback.print_exc()
        return "No response"


# Set the route and accepted methods
@mod_cmx_server.route('/add', methods=['GET', 'POST'])
def add():
    output = None
    if request.method == 'GET':
        output = render_template("cmx_server/add.html")
    else:
        try:
            name = request.form["cmx_server_name"]
            url = request.form["cmx_server_url"]
            username = request.form["cmx_server_username"]
            password = request.form["cmx_server_password"]
            externally_accessible = request.form["cmx_server_externally_accessible"] == 'True'
            cmx_server = CMXServer(name, url, username, password, externally_accessible)
            db_session.add(cmx_server)
            output = redirect(url_for('mod_cmx_server.show'))

        except:
            traceback.print_exc()
            output = redirect(url_for('error'))
            db_session.rollback()

    return output


@mod_cmx_server.route('/details/<server_id>')
def details(server_id):
    server = db_session.query(CMXServer).filter(CMXServer.id == server_id).first()
    return render_template("cmx_server/details.html", object=server)


@mod_cmx_server.route('/edit/<server_id>', methods=['GET', 'POST'])
def edit(server_id):
    output = None
    try:
        server = db_session.query(CMXServer).filter(CMXServer.id == server_id).first()
        if request.method == 'GET':
            output = render_template("cmx_server/edit.html", object=server)
        else:
            server.name = request.form["cmx_server_name"]
            server.url = request.form["cmx_server_url"]
            server.username = request.form["cmx_server_username"]
            server.password = request.form["cmx_server_password"]
            server.externally_accessible = request.form["cmx_server_externally_accessible"] == 'True'

            db_session.merge(server)
            output = redirect(url_for('mod_cmx_server.show'))

    except:
        traceback.print_exc()
        output = redirect(url_for('error'))
        db_session.rollback()

    return output


@mod_cmx_server.route('/delete/<server_id>', methods=['GET', 'POST'])
def delete(server_id):
    output = None
    try:
        server = db_session.query(CMXServer).filter(CMXServer.id == server_id).first()
        if request.method == 'GET':
            output = render_template("cmx_server/delete.html", object=server)
        else:
            server = db_session.query(CMXServer).filter(CMXServer.id == request.form["cmx_server_id"]).delete()
            output = redirect(url_for('mod_cmx_server.show'))
    except:
        traceback.print_exc()
        output = redirect(url_for('error'))
        db_session.rollback()

    return output
