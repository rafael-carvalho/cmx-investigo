#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, url_for, redirect, session
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from cenumodels import Base, User, Campus, Building, Floor, Zone, MACTrack, System, Agent, AgentsZone
import os
import json
import traceback
import time
from api.SparkAPICaller import SparkAPICaller
from api.TropoAPICaller import TropoAPICaller
from api.CMXAPICaller import CMXAPICaller
from externalapis import externalapis
import datetime
import urllib
from random import randint
import pprint
import requests_cache
import requests
import contextlib
import verticalsmapper

requests_cache.install_cache('ignore/requests_cache', backend='sqlite', expire_after=3600)

PATH_NOTIFICATIONS_WEBHOOK = "/cmx_webhook"
MSE_NOTIFICATIONS_URI = "http://{}:80{}".format(os.environ['PUBLIC_IP'], PATH_NOTIFICATIONS_WEBHOOK)
# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__, static_url_path='/static')
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

engine = create_engine(os.environ['DATABASE_URL'], convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=True,
                                         bind=engine))
socketio = SocketIO(app, async_mode=async_mode)

spark_api_caller_cenu = SparkAPICaller()
tropo_api_caller_cenu = TropoAPICaller(os.environ['TROPO_API_KEY_VOICE'], os.environ['TROPO_API_KEY_TEXT'])
floorsMapInformation = []

vertical = None

global cmx_api_caller_cenu


def init_db():
    # http://flask.pocoo.org/docs/0.11/patterns/sqlalchemy/
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()

    print ("First time running... adding tables to the database")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@app.teardown_appcontext
def shutdown_session(exception=None):
    # http://flask.pocoo.org/docs/0.11/patterns/sqlalchemy/
    db_session.commit()
    db_session.close()


@app.before_first_request
def setup():
    systems = None
    init_db()

    print ("Adding default systems")
    cenu = System("CENU", "http://10.97.40.43", "rafacarv", "Cisco1234")
    devnet = System("DevNet", "https://msesandbox.cisco.com:8081", "learning", "learning")
    coi = System("COI", "http://10.97.20.218", "rafacarv", "rewQ4321")
    db_session.add(cenu)
    db_session.add(devnet)
    db_session.add(coi)
    systems = db_session.query(System).all()

    options = []
    if (os.environ['APP_SETTINGS'] == "config.ProductionConfig"):
        options = ['CENU', 'DevNet', 'CENU']
    else:
        options = ['CENU', 'DevNet', 'COI']

    for opt in options:
        try:
            setServer(opt)
            break
        except:
            traceback.print_exc()
            print ("Server not working: {}".format(opt))


def needsToSetupServer():
    output = True
    try:
        systems = db_session.query(System).all()
        if systems is None or len(systems) == 0:
            output = True
        else:
            output = False
    except:
        output = True


def setServer(server_name, createDefaultUsers=True, subscribeToNotifications=False, verticalChosen=None):
    running_system = db_session.query(System).filter(System.name == server_name).first()
    global cmx_api_caller_cenu
    cmx_api_caller_cenu = CMXAPICaller(running_system.name, running_system.url, running_system.username,
                                       running_system.password)

    getServerHierarchiesInformation()

    if (createDefaultUsers):
        devices = []
        if (cmx_api_caller_cenu.API_SERVER_NAME.startswith("CENU") or cmx_api_caller_cenu.API_SERVER_NAME.startswith(
                "COI")):
            devices = [User("Rafael Carvalho", "78:d7:5f:1e:7e:79")]
        elif (cmx_api_caller_cenu.API_SERVER_NAME.startswith("DevNet")):
            devices = [User("DevNet 1", "00:00:2a:01:00:28"), User("DevNet 2", "00:00:2a:01:00:13"),
                       User("DevNet 3", "00:00:2a:01:00:0b"), User("DevNet 4", "00:00:2a:01:00:45"),
                       User("DevNet 5", "00:00:2a:01:00:2f"), User("DevNet 6", "00:00:2a:01:00:41"),
                       User("DevNet 7", "3a")]

        # if the vertical is None, the mapper will treat it
        global vertical
        vertical = verticalsmapper.getVertical(verticalChosen)

        mac_addresses = []
        db_session.query(User).delete()
        for obj in devices:
            db_session.add(obj)
            mac_addresses.append(obj.mac_address)

        print ("Filled database with {} default users".format(len(devices)))

        # http://www.cisco.com/c/en/us/td/docs/wireless/mse/10-1/cmx_config/CMX_Config_guide/CMX_Manage.html

        if (subscribeToNotifications):
            if (os.environ['APP_SETTINGS'] == "config.ProductionConfig" and (
                cmx_api_caller_cenu.API_SERVER_NAME.startswith(
                        "CENU") or cmx_api_caller_cenu.API_SERVER_NAME.startswith("COI"))):
                print ("Production server running with CENU MSE. Will not subscribe to notifications")
            else:
                print ("Subscribing for CMX Notifications")
                cmx_api_caller_cenu.subscribe_location_update_notification(MSE_NOTIFICATIONS_URI, mac_addresses)


def getServerHierarchiesInformation():
    campuses = []

    try:

        db_session.query(Campus).delete()
        db_session.query(MACTrack).delete()
        db_session.query(User).delete()

        if (os.environ['APP_SETTINGS'] == "config.ProductionConfig" and (
            cmx_api_caller_cenu.API_SERVER_NAME.startswith("CENU") or cmx_api_caller_cenu.API_SERVER_NAME.startswith(
                "COI"))):
            print ("Production server running with CENU MSE. Will add zone information hard-coded")
            campus = Campus(747923191153819653, "CENU")
            db_session.add(campus)
            # campus_id, aesUid, objectVersion, name
            building = Building(campus_id=campus.aesUid, aesUid=747923191153819653, objectVersion=0, name="Torre Oeste")
            db_session.add(building)

            # building_id, aesUid, calibrationModelId, objectVersion, name, floor_length, floor_width, floor_height, floor_offsetX, floor_offsetY, floor_unit, image_name, image_zoom_level, image_width, image_height, image_size, image_max_resolution, image_color_depth
            floor = Floor(building_id=building.aesUid, aesUid=747923191153819655, calibrationModelId=747923191153819656,
                          objectVersion=0, name="26andar", floor_length=133.7169, floor_width=134.50813,
                          floor_height=9.5, floor_offsetX=0, floor_offsetY=0, floor_unit="FEET",
                          image_name="domain_0_1469121487258.png", image_zoom_level=4, image_width=636,
                          image_height=632.0, image_size=636, image_max_resolution=4, image_color_depth=8)
            db_session.add(floor)

            db_session.add(Zone(floor.aesUid, "Auditorio", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Demo Room", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Jacaranda", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Sibipiruna", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Figueira", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Cedro", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Inga", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Paineira", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Tapias", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Jeriva", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Guariroba", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Seringueira", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Bambu", "ZONE"))
            db_session.add(Zone(floor.aesUid, "Cafe", "ZONE"))

            campuses = [campus]

        else:

            print ("Getting MSE zones")
            server_info = cmx_api_caller_cenu.get_all_maps()
            counter_campus = 0
            counter_buildings = 0
            counter_floors = 0
            counter_zones = 0
            campuses = []

            for campus in server_info["campuses"]:
                counter_campus = counter_campus + 1
                name = campus["name"]
                aesUid = campus["aesUid"]
                db_campus = Campus(aesUid, name, buildings=None)
                campuses.append(db_campus)
                db_session.add(db_campus)
                # print ("{})".format(name, aesUid))


                server_buildings = campus["buildingList"]
                if server_buildings is not None:
                    for b in server_buildings:
                        counter_buildings = counter_buildings + 1
                        name = b["name"]
                        aesUid = b["aesUid"]
                        objectVersion = b["objectVersion"]
                        # print ("    {}".format(name))

                        db_building = Building(db_campus.aesUid, aesUid, objectVersion, name, floors=None)
                        db_session.add(db_building)

                        server_floors = b["floorList"]
                        if server_floors is not None:
                            for f in server_floors:
                                counter_floors = counter_floors + 1
                                name = f["name"]
                                aesUid = f["aesUid"]
                                calibrationModelId = f["calibrationModelId"]

                                floor_length = f["dimension"]["length"]
                                floor_width = f["dimension"]["width"]
                                floor_height = f["dimension"]["height"]
                                floor_offsetX = f["dimension"]["offsetX"]
                                floor_offsetY = f["dimension"]["offsetY"]
                                floor_unit = f["dimension"]["unit"]

                                image_name = f["image"]["imageName"]
                                image_zoom_level = f["image"]["zoomLevel"]
                                image_width = f["image"]["width"]
                                image_height = f["image"]["height"]
                                image_size = f["image"]["size"]
                                image_max_resolution = f["image"]["maxResolution"]
                                image_color_depth = f["image"]["colorDepth"]

                                db_floor = Floor(db_building.aesUid, aesUid, calibrationModelId, objectVersion, name,
                                                 floor_length, floor_width, floor_height, floor_offsetX, floor_offsetY,
                                                 floor_unit, image_name, image_zoom_level, image_width, image_height,
                                                 image_size, image_max_resolution, image_color_depth, zones=None)
                                db_session.add(db_floor)
                                # print ("        {}".format(name))
                                server_zones = f["zones"]
                                if (server_zones is not None):
                                    counter_zones = counter_zones + 1
                                    for z in server_zones:
                                        name = z["name"]
                                        zone_type = z["zoneType"]
                                        # print ("            {}".format(name))
                                        db_zone = Zone(db_floor.aesUid, name, zone_type)
                                        db_session.add(db_zone)

                print (
                "{} has {} buildings, {} floors, {} zones".format(db_campus.name, counter_buildings, counter_floors,
                                                                  counter_zones))

        floors = db_session.query(Floor).all()
        print ("Downloading floors images")
        for floor in floors:
            try:
                filename = 'static/maps/' + floor.name + ".png"
                """
                response = cmx_api_caller_cenu.download_hierarchy_image(floor.image_name)
                filename = 'static/maps/'+ floor.name + ".png"
                with open(filename,"wb") as fo:
                    #fo.write("This is Test Data")
                    fo.write(response.content)
                    fo.close()

                    mapInfo = {}
                    mapInfo['map'] = url_for('static', filename="maps/{}.png".format(floor.name))
                    mapInfo['floorWidth'] = str(floor.floor_width)
                    mapInfo['floorHeight'] = str(floor.floor_height)
                    mapInfo['floorLength'] =  str(floor.floor_length)
                    mapInfo['imgWidth'] = str(floor.image_width)
                    mapInfo['imgHeight'] = str(floor.image_height)

                    mapInfoPair = {
                                   'name' : floor.name,
                                   'mapInfo' : mapInfo
                                   }

                    floorsMapInformation.append(mapInfoPair)
                """

                mapInfo = {}
                mapInfo['map'] = url_for('static', filename="maps/{}.png".format(floor.name))
                mapInfo['floorWidth'] = str(floor.floor_width)
                mapInfo['floorHeight'] = str(floor.floor_height)
                mapInfo['floorLength'] = str(floor.floor_length)
                mapInfo['imgWidth'] = str(floor.image_width)
                mapInfo['imgHeight'] = str(floor.image_height)

                mapInfoPair = {
                    'name': floor.name,
                    'mapInfo': mapInfo
                }
                global floorsMapInformation
                floorsMapInformation.append(mapInfoPair)
                # url = cmx_api_caller_cenu.__build_image_source_map_base_URL() + "/" + f.image_name
                # urllib.urlretrieve(url, '/static/img/'+f.image_name)
                # path = '/static/img/' + f.image_name
                # f = open(path, 'wb')
                # f.write(response.content)

            except:
                # traceback.print_exc()
                pass

    except:
        print ("Error getting hierarchy information from server")
        traceback.print_exc()


@app.route(PATH_NOTIFICATIONS_WEBHOOK, methods=['GET', 'POST'])
def cmx_webhook():
    # https://developer.cisco.com/site/cmx-mobility-services/learn/tutorials/node-js-listener/
    # https://msesandbox.cisco.com:8081/manage/#notifications
    output_text = "Empty"
    try:
        if (request.data):
            # It means the request was originated from CMX
            requestJson = request.json
            notifications = requestJson["notifications"]
        else:
            # It means the request was originated from the App from the simulation page
            messages = session['messages']
            messages = json.loads(messages)
            notifications = messages['notifications']

        for notification in notifications:
            notificationType = notification["notificationType"]

            if (notificationType == "absence"):
                output_text = process_absence_notification(notification)
            else:

                confidence_factor = notification["confidenceFactor"]
                map_hierarchy = notification["locationMapHierarchy"]
                floorId = notification["floorId"]
                mac_address = notification["deviceId"]

                if (confidence_factor > 40):
                    output_text = "Confidence factor = {}".format(confidence_factor)
                    hierarchies = map_hierarchy.split(">")
                    notification_floor_name = hierarchies[2].strip()
                    # print (json.dumps(requestJson))

                    # floor = .query(Floor).filter(Floor.aesUid == floorId).first()
                    floor = db_session.query(Floor).filter(Floor.name == notification_floor_name).first()
                    if (floor is None):
                        output_text = "Received a notification for floor {} (id = {}), which is not on this system.".format(
                            notification_floor_name, floorId)
                    else:
                        if (notificationType == "locationupdate"):
                            output_text = process_location_update_notification(notification, floor)
                        else:
                            output_text = "Received notification (type = {})... Pass".format(notificationType,
                                                                                             mac_address)
                else:
                    output_text = "Confidence factor ({}) was too low. Ignoring {} for {}...".format(confidence_factor,
                                                                                                     notificationType,
                                                                                                     mac_address)


    except:
        db_session.rollback()
        print ("Error handling CMX Notification!")
        traceback.print_exc()
        output_text = "Error!"

    finally:
        print (output_text)

    return output_text


def process_area_change_notification(notification, user):
    moveDistanceInFt = notification["moveDistanceInFt"]
    if (moveDistanceInFt > 0):
        map_hierarchy = notification["locationMapHierarchy"]
        output_text = "{} changed to area {}".format(user, map_hierarchy)
        print (output_text)
        spark_api_caller_cenu.postMessage(
            "Y2lzY29zcGFyazovL3VzL1JPT00vYTY0NDFmMDAtNWZmNC0xMWU2LTkwODctN2IzY2QxMWYwYzg3", None, None, output_text,
            None, None)
        # tropo_api_caller_cenu.triggerTropoWithMessageAndNumber(output_text, "+5511975437609", type="text")
    else:
        output_text = "Received notification (type = Area Change) for {}, but the move distance was 0... Skipping".format(
            user)
        print (output_text)
    return output_text


def process_movement_notification(notification, user):
    moveDistanceInFt = notification["moveDistanceInFt"]
    map_hierarchy = notification["locationMapHierarchy"]
    output_text = "{} moved {} feet. Current area: {}".format(user, moveDistanceInFt, map_hierarchy)
    spark_api_caller_cenu.postMessage("Y2lzY29zcGFyazovL3VzL1JPT00vYTY0NDFmMDAtNWZmNC0xMWU2LTkwODctN2IzY2QxMWYwYzg3",
                                      None, None, output_text, None, None)
    # tropo_api_caller_cenu.triggerTropoWithMessageAndNumber(output_text, "+5511975437609", type="text")
    return output_text


def process_absence_notification(notification):
    mac_address = notification["deviceId"]

    previousHierarchy = engine.execute(
        "SELECT hierarchy from mactrack where mac_address = '{}'".format(mac_address)).first()
    if previousHierarchy:
        #    previousHierarchy = row[0]
        previousHierarchy = previousHierarchy[0]
        db_session.query(MACTrack).filter(MACTrack.mac_address == mac_address).delete()

    name = "Unknown device"
    user = db_session.query(User).filter(User.mac_address == mac_address).first()
    if (user):
        name = user.name

    if (user and previousHierarchy):
        # user was on the system, but then left... let's update any engagement screen that was showing info to him / her.
        updateEngagementScreen(previousHierarchy, user, False)

    lastSeen = notification["lastSeen"]

    hierarchies = get_updated_hierarchies()
    updateDeviceScreen(mac=mac_address, name=name, lastSeen=lastSeen, absent=True, hierarchy=previousHierarchy,
                       mapCoordinateX=0, mapCoordinateY=0)
    updateHierarchiesScreens(hierarchies)
    updateOverviewScreen(hierarchies)

    output_text = "{} ({}) has left the system.".format(name, mac_address)
    return output_text


def process_location_update_notification(notification, floor):
    mac_address = notification["deviceId"]

    confidence_factor = notification["confidenceFactor"]
    map_hierarchy = notification["locationMapHierarchy"]
    hierarchies = map_hierarchy.split(">")

    """
    b = list(filter(lambda h: h.name == hierarchies[1].strip(), campus.buildings))[0]
    floor = list(filter(lambda h: h.name == hierarchies[2].strip(), b.floors))[0]
    """

    mac = notification["deviceId"]
    mapCoordinateX = notification["locationCoordinate"]["x"]
    mapCoordinateY = notification["locationCoordinate"]["y"]
    lastSeen = notification["lastSeen"]

    floorWidth = floor.floor_width
    floorHeight = floor.floor_height
    floorLength = floor.floor_length
    imgWidth = floor.image_width
    imgHeight = floor.image_height

    # Update mactrack table
    userWasSomewhereElse = False
    userWasAlreadyHere = False
    previousHierarchy = engine.execute(
        "SELECT hierarchy from mactrack where mac_address = '{}'".format(mac_address)).first()

    if previousHierarchy:
        #    previousHierarchy = row[0]
        previousHierarchy = previousHierarchy[0]
        if (previousHierarchy != map_hierarchy):
            # User was already being tracked, but in a different hierarchy

            userWasSomewhereElse = True
        else:
            userWasAlreadyHere = True

        db_session.query(MACTrack).filter(MACTrack.mac_address == mac_address).delete()

    mactrack = MACTrack(mac_address, map_hierarchy, lastSeen, mapCoordinateX, mapCoordinateY)
    db_session.merge(mactrack)

    hierarchies = get_updated_hierarchies()
    # hierarchies = []

    name = "Unknown device"
    user = db_session.query(User).filter(User.mac_address == mac_address).first()
    if user:
        name = user.name
        if (previousHierarchy and userWasSomewhereElse):
            # User was in a zone with engagement screen and then moved to another one
            updateEngagementScreen(previousHierarchy, user, False)

        if (not userWasAlreadyHere):
            # update the engagement screen on the other hierarchy
            updateEngagementScreen(map_hierarchy, user, True)
            splittedHierarchy = map_hierarchy.split(">")
            zoneOrFloor = splittedHierarchy[-1]
            floorOrBuilding = splittedHierarchy[-2]

            text = "VIP client {} is at {}.".format(user.name, map_hierarchy)

            text = "Cliente {} entrou na area de {} no {}".format(user.name,
                                                                  verticalsmapper.getEquivalentHierarchy(zoneOrFloor),
                                                                  verticalsmapper.getEquivalentHierarchy(
                                                                      floorOrBuilding))
            text = "Client / asset {} entered in the area {} @ {}".format(user.name,
                                                                          verticalsmapper.getEquivalentHierarchy(
                                                                              zoneOrFloor),
                                                                          verticalsmapper.getEquivalentHierarchy(
                                                                              floorOrBuilding))

            """
            db_hierarchy = list(filter(lambda h: h['name'] == map_hierarchy, hierarchies))[0] #filters the list of dict to find the hierarchy with the name
            if (len (db_hierarchy["users"]) > 1):
                #text += " There are {} other VIP clients in the area.".format(len(db_hierarchy["users"]) - 1)
                #text += " Existem outros {} clientes na mesma area.".format(len(db_hierarchy["users"]) - 1)
                pass
            if (len (db_hierarchy["unknown_devices"]) > 1):
                #text += " There are {} other devices in the area.".format(len(db_hierarchy["unknown_devices"]) - 1)
                #There are {} other devices in the area, {} of them are registered users".format()
                pass
            """
            hotspotTriggers = verticalsmapper.getHotspotTriggers(zoneOrFloor, vertical)
            for trigger in hotspotTriggers:
                platform = trigger['platform']
                if (platform == verticalsmapper.PLATFORM_SPARK):
                    for val in trigger['value']:
                        try:
                            spark_api_caller_cenu.postMessage(val, None, None, text, None, None)
                        except:
                            print('Error posting to Spark')

                elif (platform == verticalsmapper.PLATFORM_TROPO):
                    for val in trigger['value']:
                        for number in val['text']:
                            try:
                                tropo_api_caller_cenu.triggerTropoWithMessageAndNumber(text, number, type="text")
                            except:
                                print('Error posting to Tropo')
                        for number in val['voice']:
                            try:
                                tropo_api_caller_cenu.triggerTropoWithMessageAndNumber(text, number, type="voice")
                            except:
                                print('Error posting to Tropo')
                                # if ("VIP" in user.name):

            """
            spark_api_caller_cenu.postMessage("Y2lzY29zcGFyazovL3VzL1JPT00vYTY0NDFmMDAtNWZmNC0xMWU2LTkwODctN2IzY2QxMWYwYzg3", None, None, text, None, None)
            tropo_api_caller_cenu.triggerTropoWithMessageAndNumber(text, "+5511975437609", type="text")
            number_voice = "sip:rafacarv@cisco.com;transport=tcp"
            response = tropo_api_caller_cenu.triggerTropoWithMessageAndNumber(text, number_voice, type="voice")
            """

    updateDeviceScreen(mac=mac, name=name, lastSeen=lastSeen, hierarchy=map_hierarchy, mapCoordinateX=mapCoordinateX,
                       mapCoordinateY=mapCoordinateY, floorWidth=floorWidth, floorHeight=floorHeight,
                       floorLength=floorLength, imgWidth=imgWidth, imgHeight=imgHeight, absent=False)
    updateHierarchiesScreens(hierarchies)
    updateOverviewScreen(hierarchies)
    output_text = "{} ({}) location updated. Current area: {}.".format(name, mac_address, map_hierarchy)
    return output_text


def process_in_out_notification(notification, user):
    notification_name = notification["subscriptionName"]
    map_hierarchy = notification["locationMapHierarchy"]
    boundary = notification["boundary"]

    if (boundary.lower() == "inside"):
        output_text = "{} just entered {}.".format(user, map_hierarchy)

    elif (boundary.lower() == "outside"):
        output_text = "{} just left {}.".format(user, map_hierarchy)

    spark_api_caller_cenu.postMessage("Y2lzY29zcGFyazovL3VzL1JPT00vYTY0NDFmMDAtNWZmNC0xMWU2LTkwODctN2IzY2QxMWYwYzg3",
                                      None, None, output_text, None, None)
    # tropo_api_caller_cenu.triggerTropoWithMessageAndNumber(output_text, "+5511975437609", type="text")
    return output_text


def get_updated_hierarchies():
    tracked = db_session.query(MACTrack).all()
    db_users = db_session.query(User).all()

    hierarchies = []
    users = []

    for t in tracked:
        mac_address = t.mac_address

        found = False
        hierarchy = None

        searchHierarchy = filterList(hierarchies, 'name', t.hierarchy)
        if (len(searchHierarchy) > 0):
            hierarchy = searchHierarchy[0]

        if hierarchy is None:
            hierarchy = {}
            hierarchy["name"] = t.hierarchy
            hierarchy["verticalName"] = verticalsmapper.getEquivalentHierarchy(t.hierarchy, vertical)
            hierarchy["limit"] = verticalsmapper.getOccupancyLimit(t.hierarchy, vertical)
            hierarchy["users"] = []
            hierarchy["unknown_devices"] = []

            parts = t.hierarchy.split(">")
            floorName = parts[2].strip()

            hierarchy['mapInfo'] = getMapInfo(floorName)
            hierarchies.append(hierarchy)

        user = None
        for u in db_users:
            if u.mac_address == t.mac_address:
                user = u
                break

        if user:
            user_data = {
                "info": user.serialize(),
                "coordinates": {
                    "x": str(t.coord_x),
                    "y": str(t.coord_y)
                }
            }
            hierarchy["users"].append(user_data)
        else:
            device_data = {
                "mac_address": t.mac_address,
                "coordinates": {
                    "x": str(t.coord_x),
                    "y": str(t.coord_y)
                }
            }
            hierarchy["unknown_devices"].append(device_data)

    return hierarchies


def getMapInfo(floorName):
    output = list(filter(lambda f: f['name'] == floorName, floorsMapInformation))[
        0]  # filters the list of dict to find the hierarchy with the name
    return output['mapInfo']


def filterList(searchList, keyName, value):
    try:
        output = filter(lambda f: f[keyName] == value,
                        searchList)  # filters the list of dict to find the hierarchy with the name
    except:
        output = None
    return output


def getFloorsWithZones():
    floors = db_session.query(Floor).all()
    hierarchies = []

    for f in floors:
        h = {
            'name': f.getHierarchy(),
            'verticalName': verticalsmapper.getEquivalentHierarchy(f.getHierarchy(), vertical),
            'type': 'floor'
        }
        zones = []
        for zone in f.zones:
            z = {
                'name': zone.getHierarchy(),
                'verticalName': verticalsmapper.getEquivalentHierarchy(zone.getHierarchy(), vertical),
                'type': "zone"
            }
            zones.append(z)
        h['zones'] = zones
        hierarchies.append(h)

    return hierarchies


@app.route('/hierarchy/<hierarchy>')
@app.route('/hierarchy')
def hierarchy(hierarchy=None):
    if (hierarchy is not None):
        output = render_template('hierarchy.html', hierarchy=hierarchy,
                                 verticalHierarchy=verticalsmapper.getEquivalentHierarchy(hierarchy, vertical),
                                 limit=verticalsmapper.getOccupancyLimit(hierarchy, vertical))
    else:
        hierarchies = getFloorsWithZones()
        output = render_template('hierarchy_select.html', hierarchies=hierarchies, url=url_for('hierarchy'))

    return output


@app.route('/device/<mac>')
@app.route('/device')
def device(mac=None):
    output = None
    if (mac is not None):
        user = db_session.query(User).filter(User.mac_address == mac).first()
        if (user):
            name = user.name
        else:
            name = "Unknown device"
        payload = {
            'mac': mac,
            'name': name,
            'updated': "Never",
            'absent': True
        }
        try:
            serverOutput = cmx_api_caller_cenu.get_client_information(mac, timeout=5)
            # print (json.dumps(serverOutput, indent=4))
            currentlyTracked = serverOutput["currentlyTracked"]
            lastSeen = serverOutput["statistics"]["lastLocatedTime"]
            if (not currentlyTracked):
                payload = {
                    'mac': mac,
                    'name': name,
                    'updated': lastSeen,
                    'absent': True
                }

            else:
                mapInfo = serverOutput["mapInfo"]

                hierarchy = mapInfo["mapHierarchyString"]
                floor = hierarchy.split(">")[2].strip()
                map_path = url_for('static', filename="maps/{}.png".format(floor))

                hierarchy = verticalsmapper.getEquivalentHierarchy(hierarchy, vertical)
                floor = db_session.query(Floor).filter(Floor.name == floor).first()

                floorWidth = str(floor.floor_width)
                floorHeight = str(floor.floor_height)
                floorLength = str(floor.floor_length)
                imgWidth = str(floor.image_width)
                imgHeight = str(floor.image_height)
                mapCoordinateX = serverOutput["mapCoordinate"]["x"]
                mapCoordinateY = serverOutput["mapCoordinate"]["y"]

                map_path = url_for('static', filename="maps/{}.png".format(floor.name))

                payload = {
                    'mac': mac,
                    'name': name,
                    'mapCoordinateX': str(mapCoordinateX),
                    'mapCoordinateY': str(mapCoordinateY),
                    'floorWidth': str(floorWidth),
                    'floorHeight': str(floorHeight),
                    'floorLength': str(floorLength),
                    'imgWidth': str(imgWidth),
                    'imgHeight': str(imgHeight),
                    'updated': lastSeen,
                    'hierarchy': hierarchy,
                    'map': map_path,
                    'absent': False
                }
        except:
            # traceback.print_exc()
            # Probably this device has never been tracked, or was an invalid MAC, or the server can't reach the GET API
            pass
        finally:
            output = render_template('device.html', mac=mac, msg=json.dumps(payload))

    else:
        tracks = db_session.query(MACTrack).order_by("last_modified desc").all()
        output = render_template('device_select.html', url=url_for('device'), tracks=tracks)

    return output


@app.route('/simulation', methods=['GET', 'POST'])
def simulation():
    output = None
    if request.method == 'POST':
        hierarchy = request.form["hierarchy"]
        coord_x = request.form["coord_x"]
        coord_y = request.form["coord_y"]
        mac = request.form["mac_address"]
        event = request.form["event"]
        if (not mac):
            mac = request.form["mac_address_user"]

        if (mac and hierarchy and coord_x and coord_y):
            payload = {
                "deviceId": mac,
                "locationMapHierarchy": hierarchy,
                "confidenceFactor": 100,
                "locationCoordinate": {
                    "z": 0,
                    "y": coord_y,
                    "x": coord_x,
                    "unit": "FEET"
                },
                "lastSeen": "2016-09-28T02:10:53.810+0100",
                "notificationType": event,
                "floorId": 723413320329068500,
            }
            payload = {

                "notifications": [payload]

            }
            payload = json.dumps(payload)
            session['messages'] = payload
            output = redirect(url_for('cmx_webhook'))
        else:
            output = redirect(url_for('simulation'))

    else:
        output = render_template('simulation.html', hierarchies=getFloorsWithZones(),
                                 users=db_session.query(User).all())

    return output


@app.route('/engagement/<hierarchy>', methods=['GET'])
@app.route('/engagement', methods=['GET'])
def engagement(hierarchy=None):
    if (hierarchy is not None):
        output = render_template('engagement_screen.html', hierarchy=hierarchy,
                                 verticalHierarchy=verticalsmapper.getEquivalentHierarchy(hierarchy, vertical))
    else:

        hierarchies = getFloorsWithZones()
        output = render_template('engagement_screen_select.html', hierarchies=hierarchies, url=url_for('engagement'))

    return output


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/overview')
def overview():
    return render_template('overview.html', device_url=url_for('device', mac=""),
                           hierarchyUrl=url_for('hierarchy', hierarchy=""))


@app.route('/users', methods=['GET'])
def users():
    output = None
    users = db_session.query(User).all()
    userUrl = url_for('user', mac_address="")
    output = render_template('users.html', users=users, userUrl=userUrl, deviceUrl=url_for('device', mac=""))
    return output


@app.route('/user/<mac_address>', methods=['GET', 'POST'])
@app.route('/user', methods=['GET', 'POST'])
def user(mac_address=None):
    output = None
    if request.method == 'POST':

        name = request.form["name"]
        phone = request.form["phone"]
        mac_address = request.form["mac_address"]
        try:
            user = User(name, mac_address, phone)
            db_session.merge(user)
            output = redirect(url_for('users'))
        except:
            output = "Error trying to add users"
            traceback.print_exc()
    else:
        user = None
        if (mac_address):
            user = db_session.query(User).filter(User.mac_address == mac_address).first()

        output = render_template('user_edit.html', user=user, mac_address=mac_address)

    return output


@app.route('/user/delete/<mac_address>', methods=['GET', 'POST'])
def user_delete(mac_address):
    output = None
    if request.method == 'POST':
        mac_address = request.form["mac_address"]
        try:
            db_session.query(User).filter(User.mac_address == mac_address).delete()
            output = redirect(url_for('users'))
        except:
            output = "Error trying to delete user with MAC = {}".format(mac_address)
            traceback.print_exc()
    else:
        user = db_session.query(User).filter(User.mac_address == mac_address).first()
        output = render_template('user_delete.html', user=user)

    return output


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    output = None
    if request.method == 'POST':
        req = request.form
        server_name = request.form["server"]
        subscribe = request.form["subscribe"] == 'True'
        default_users = request.form["default_users"] == 'True'
        vertical = request.form["vertical"]
        if (vertical == "None"):
            vertical = None
        print (
        "Setting server to {}. Subscribe to notifications: {}. Adding Users: {}. Vertical: {}".format(server_name,
                                                                                                      subscribe,
                                                                                                      default_users,
                                                                                                      vertical))
        try:
            setServer(server_name, createDefaultUsers=default_users, subscribeToNotifications=subscribe,
                      verticalChosen=vertical)
            output = redirect(url_for('settings'))
        except:
            output = "Error trying to change system's settings"
    else:
        if (needsToSetupServer()):
            setup()
        systems = db_session.query(System).all()
        output = render_template('settings.html', systems=systems, verticals=verticalsmapper.VERTICALS)

    return output


def updateDeviceScreen(mac, name="Unknown device", lastSeen=None, hierarchy=None, mapCoordinateX=None,
                       mapCoordinateY=None, floorWidth=None, floorHeight=None, floorLength=None, imgWidth=None,
                       imgHeight=None, absent=False):
    if (lastSeen is None):
        lastSeen = str(datetime.datetime.now())

    namespace = mac

    if (not absent):
        parts = hierarchy.split(">")
        hierarchies = hierarchy.split(">")
        campus_name = hierarchies[0].strip()
        building = hierarchies[1].strip()
        floor = hierarchies[2].strip()
        map_path = url_for('static', filename="maps/{}.png".format(floor))

        payload = {
            'mac': mac,
            'name': name,
            'mapCoordinateX': str(mapCoordinateX),
            'mapCoordinateY': str(mapCoordinateY),
            'floorWidth': str(floorWidth),
            'floorHeight': str(floorHeight),
            'floorLength': str(floorLength),
            'imgWidth': str(imgWidth),
            'imgHeight': str(imgHeight),
            'updated': lastSeen,
            'hierarchy': hierarchy,
            'map': map_path,
            'absent': absent
        }
    else:
        payload = {
            'mac': mac,
            'name': name,
            'updated': lastSeen,
            'absent': absent
        }
        # This means that the device was somewhere else before leaving the system
        if (mapCoordinateX and mapCoordinateY and hierarchy):
            payload['mapCoordinateX'] = str(mapCoordinateX)
            payload['mapCoordinateY'] = str(mapCoordinateY)
            payload['hierarchy'] = hierarchy

    socketio.emit('my_response', payload, namespace='/' + namespace)


def updateHierarchiesScreens(hierarchies):
    for h in hierarchies:
        # print ("Updating {}".format(h["name"]))
        payload = {
            'hierarchy': h,
        }

        socketio.emit('my_response', payload, namespace='/' + h["name"])


def updateOverviewScreen(hierarchies):
    payload = {
        'hierarchies': hierarchies,
    }

    socketio.emit('my_response', payload, namespace='/overview')


def updateEngagementScreen(hierarchy, user, entering=True):
    if (entering):
        stock = "CSCO"
        city = "New York"
        payload = {
            'user': user.serialize(),
            'hierarchy': hierarchy,
            'weather': externalapis.getTemperature(city),
            # 'flight' : flight,
            # 'traffic' : traffic,
            'market': externalapis.getStockQuote(stock),
            'entering': True
        }
    else:
        payload = {
            'user': user.serialize(),
            'entering': False
        }
    nmspace = '/engagement/{}'.format(hierarchy)
    print("updating engagement {}".format(nmspace))
    socketio.emit('my_response', payload, namespace=nmspace)


def addAgentToZone(agent, zone):
    association = AgentsZone()
    association.zone = zone
    association.agent = agent
    zone.agents.append(association)


@app.route('/agent')
def agent():
    output = "None"
    try:
        a1 = Agent("Agent 4")
        a2 = Agent("Agent 5")
        db_session.add(a1)
        db_session.add(a2)

        z1 = db_session.query(Zone).first()

        addAgentToZone(a1, z1, session)
        addAgentToZone(a2, z1, session)

        associations = z1.agents
        output = ''
        for association in associations:
            output += association.agent.name

        print output

    except:
        db_session.rollback()
        output = "Error!"
        traceback.print_exc()

    return output


if __name__ == '__main__':
    """
    currentServerTime = "2016-08-17T20:05:32.368-0300"[:-5]


    lastSeen = "2016-08-17T16:17:42.957-0300"
    lastSeen_without_timezone = lastSeen[:-5]
    timezone_server = lastSeen[-5:]
    now = datetime.datetime.now()


    lastLocatedTime = "2016-08-17T20:05:26.957-0300"[:-5]

    lastSeen = datetime.datetime.strptime(lastSeen, "%Y-%m-%dT%H:%M:%S.%f")
    lastLocatedTime = datetime.datetime.strptime(lastLocatedTime, "%Y-%m-%dT%H:%M:%S.%f")
    delta = currentServerTime - lastLocatedTime

    deltaFormmated = delta.seconds
    #delta = (str(delta)).split()
    #delta = delta[0] + " " + delta[1]
    print ("Located {} seconds ago".format(deltaFormmated))
    """
    socketio.run(app, port=5000, debug=True)


