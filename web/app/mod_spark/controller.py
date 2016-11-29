from flask import Blueprint, request, url_for
import traceback
import json
import os
import datetime
from app import app
from app import get_api_spark
from app.database import db_session
from app.mod_user.models import RegisteredUser
from app.mod_api.controller import get_device_location
import plotly.plotly as py
import plotly.graph_objs as go
import numpy as np
py.sign_in('rafacarv', 'zMrWUiu61ulJhbKBLSSV')


mod_spark = Blueprint('mod_spark', __name__, url_prefix='/spark')

@mod_spark.route('/', methods=['GET', 'POST'])
def home():
    output = "Empty"
    try:
        parsed_input = parse_user_input(request)

        message = parsed_input["message"]
        message_id = parsed_input["message_id"]
        person_id = parsed_input["person_id"]
        person_email = parsed_input["person_email"]
        room_id = parsed_input["room_id"]

        # this logs the message on the console
        print ("Received: {}".format(message))

        # Build here the message that you want to post back on the same Spark room.
        will_reply_something = False

        # Setting up some default values for the message to be posted.
        post_roomId = room_id  # Usually it's the same room where you received the message.
        post_to_person_id = None  #
        post_to_person_email = None
        post_text = None
        post_markdown = None
        post_files = None

        # Here you will analyze all the messages received on the room and react to them
        if message.lower().strip().startswith('find'):
            message = message.replace('find', '').strip()
            mac = None
            if message.lower().strip().startswith('user'):
                content = message.replace('user', '').strip()
                user = db_session.query(RegisteredUser).filter(RegisteredUser.name == content).first()

                if user:
                    mac = user.mac_address
                else:
                    post_text = "I am sorry. I could not find any user named {}".format(content)

            else:
                mac = message

            if mac:
                location = get_device_location(mac, True)
                print(json.dumps(location, indent=2))
                location = location['unknown_devices'] + location['registered_users']
                if len(location) > 0:
                    location = location[0]['location']
                    map_path = location['map_information']['map_path'].replace('/static/', '')
                    filename = os.path.join(app.static_folder, map_path)
                    """
                    from matplotlib import pyplot as plt
                    im = plt.imread(filename)
                    implot = plt.imshow(im)
                    plt.scatter(location['coord_x'], location['coord_y'])
                    filename = os.path.join(app.static_folder, 'maps/test.png')
                    plt.savefig(filename)
                    post_files = [filename]
                    print(post_files)
                    #files = {'file': ('report.xls', open('report.xls', 'rb'), 'type=image/png', {'Expires': '0'})}
                    """
                    #filename = plot_point_over_image(filename, location['coord_x'], location['coord_y'])
                    #(background_image_path, coord_x, coord_y, image_width, image_height):)

                    post_text = 'Device is at {}. Coordinates: ({}, {}). Information obtained {} ago'.format(location['hierarchy'], location['coord_x'], location['coord_y'], location['last_modified_ago'])
                else:
                    post_text = 'Device not found'
        if not post_text:
            post_text = 'Unidentified command'

        write_to_spark(post_roomId, post_to_person_id, post_to_person_email, post_text, post_markdown, post_files)

    except Exception as e:
        traceback.print_exc()
        post_text = str(e)

    # The return of the message will be sent via HTTP (not to Spark, but to the client who requested it)
    return post_text


def parse_user_input(req):
    """Helper function to parse the information received by spark."""

    http_method = None

    if req.method == "GET":
        http_method = "GET"
        message = req.args["message"]
        message_id = "FAKE"
        person_id = "FAKE"
        person_email = "FAKE"
        room_id = "Y2lzY29zcGFyazovL3VzL1JPT00vYTY0NDFmMDAtNWZmNC0xMWU2LTkwODctN2IzY2QxMWYwYzg3"

    elif req.method == "POST":
        http_method = "POST"

        # Get the json data from HTTP request. This is what was written on the Spark room, which you are monitoring.
        requestJson = req.json
        # print (json.dumps(reqJson))

        # parse the message id, person id, person email, and room id
        message_id = requestJson["data"]["id"]
        person_id = requestJson["data"]["personId"]
        person_email = requestJson["data"]["personEmail"]
        room_id = requestJson["data"]["roomId"]

        # At first, Spark does not give the message itself, but it gives the ID of the message. We need to ask for the content of the message
        message = read_from_spark(message_id)

    else:
        output = "Error parsing user input on {} method".format(http_method)
        raise Exception(output)

    output = {"message": message, "message_id": message_id, "person_id": person_id, "person_email": person_email,
              "room_id": room_id}
    return output


def read_from_spark(message_id):
    try:
        message = get_api_spark().getMessage(message_id)
    except:
        raise Exception("Error while trying to READ from Spark.")
    return message


def write_to_spark(room_id, to_person_id, to_person_email, text, markdown, files):
    try:
        if room_id != "FAKE":
            get_api_spark().messages.create(files=files, roomId=room_id, text=text)
    except:
        traceback.print_exc()
        raise Exception("Error while trying to WRITE to Spark.")


@mod_spark.route('/plot', methods=['GET'])
def plot():
    # Ideas
    # plot_point_over_image('maps/IDEAS.png', 10, 10, 568, 1080, 15, 39)
    # DevNet Zone
    filename = plot_point_over_image('maps/DevNetZone.png', 10, 10, 2038, 544, 307, 16.5)
    path = url_for('static', filename=filename, _external=True)
    html = '<a href="{}">{}</a>'.format(path, path)



    html = '<img src="{}" />'.format(path)
    return html


def plot_point_over_image(background_image_path, coord_x, coord_y, image_width, image_height, floor_width, floor_height):
    return plot_point_over_image_new(background_image_path, coord_x, coord_y, image_width, image_height, floor_width, floor_height)


def plot_point_over_image_model(background_image_path, coord_x, coord_y, image_width, image_height, floor_width, floor_height):
    """
    DON'T USE ME
    """
    # https://plot.ly/python/reference/#layout-images
    trace1 = go.Scatter(x=[0], y=[0])
    layout = go.Layout(images=[dict(
        # source="https://images.plot.ly/language-icons/api-home/python-logo.png",
        source="http://cmx-finder.herokuapp.com/static/maps/DevNetZone.png",
        xref="0",
        yref="0",
        xanchor='left',
        yanchor='bottom',
        x=0,
        y=0,
        sizex=1,
        sizey=1,
        sizing="contain",
        opacity=1,
        layer="above")])
    fig = go.Figure(data=[trace1], layout=layout)
    file_path = 'maps_plotted/my_image-{}.png'.format(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    saved_file_name = '/Users/rafacarv/workspace/cmx-finder-container/web/app/static/' + file_path
    py.image.save_as(fig, saved_file_name)
    return file_path


def plot_point_over_image_new(background_image_path, coord_x, coord_y, image_width, image_height, floor_width, floor_height):
    # https://plot.ly/python/reference/#layout-images
    trace1 = go.Scatter(x=[0], y=[0])
    layout = go.Layout(images=[dict(
        # source="https://images.plot.ly/language-icons/api-home/python-logo.png",
        source="http://cmx-finder.herokuapp.com/static/maps/DevNetZone.png",
        xref="x",
        yref="y",
        xanchor='left',
        yanchor='bottom',
        x=0,
        y=0,
        sizex=1,
        sizey=1,
        sizing="contain",
        opacity=1,
        layer="above")])
    fig = go.Figure(data=[trace1], layout=layout)
    file_path = 'maps_plotted/my_image-{}.png'.format(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    saved_file_name = '/Users/rafacarv/workspace/cmx-finder-container/web/app/static/' + file_path
    py.image.save_as(fig, saved_file_name)
    return file_path