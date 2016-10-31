'''
Created on Jul 27, 2016

@author: rafacarv
'''
#http://flask-sqlalchemy.pocoo.org/2.1/models/
#https://realpython.com/blog/python/flask-by-example-part-2-postgres-sqlalchemy-and-alembic/

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql.sqltypes import Numeric, DateTime, BigInteger

from app.database import Base


class CMXServer(Base):
    __tablename__ = 'cmx_server'
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String, unique=True)
    url = Column(String, unique=True)
    username = Column(String)
    password = Column(String)
    externally_accessible = Column(Boolean)
    active = Column(Boolean)
    cmx_system = relationship("CMXSystem", cascade="all, delete-orphan", single_parent=True)
    cmx_system_id = Column(Integer, ForeignKey('cmx_system.id', ondelete='cascade'))

    def __init__(self, name, url, username, password, active, externally_accessible):
        self.name = name
        self.url = url
        self.username = username
        self.password = password
        self.active = active
        self.externally_accessible = externally_accessible

    def __repr__(self):
        return "{} ({})".format(self.name, self.url)

    def get_hierarchies(self):
        return self.cmx_system.campuses



class CMXSystem(Base):
    __tablename__ = 'cmx_system'
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String)
    campuses = relationship("Campus", cascade="all, delete-orphan", lazy='dynamic')

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "{}".format(self.name)

    def get_floors(self):
        floors = []
        for c in self.campuses:
            for b in c.buildings:
                floors.append(b.floors)


class Campus(Base):
    __tablename__ = "campus"
    aes_uid = Column(BigInteger, primary_key=True, unique=True)
    name = Column(String, unique=True)
    cmx_system_id = Column(Integer, ForeignKey('cmx_system.id', ondelete='cascade'))
    cmx_system = relationship("CMXSystem", back_populates="campuses")
    buildings = relationship("Building", cascade="all, delete-orphan", lazy='dynamic')

    def __init__(self, aes_uid, name, buildings=None):
        self.aes_uid = aes_uid
        self.name = name
        if (buildings is not None):
            self.buildings = buildings

    def __repr__(self):
        return "{}".format(self.name)

    def get_hierarchy(self):
        return self.name


class Building(Base):
    __tablename__ = "building"
    aes_uid = Column(BigInteger, primary_key=True, unique=True)
    object_version = Column(Integer, default=0)
    name = Column(String, unique=True)
    campus_id = Column(BigInteger, ForeignKey('campus.aes_uid', ondelete='cascade'))
    campus = relationship("Campus", back_populates="buildings")
    floors = relationship("Floor", cascade="all, delete-orphan", lazy='dynamic')

    def __init__(self, campus_id, aes_uid, object_version, name, floors=None):
        self.aes_uid = aes_uid
        self.object_version = object_version
        self.name = name
        self.campus_id = campus_id
        if floors is not None:
            self.floors = floors

    def __repr__(self):
        return "{}".format(self.name)

    def get_hierarchy(self):
        return "{}>{}".format(self.campus.get_hierarchy(), self.name)


class Floor(Base):
    __tablename__ = "floor"
    building_id = Column(BigInteger, ForeignKey('building.aes_uid', ondelete='cascade'))
    building = relationship("Building", back_populates="floors")
    aes_uid = Column(BigInteger, primary_key=True, unique=True)
    calibration_model_id = Column(BigInteger)
    object_version = Column(Integer, default=0)
    name = Column(String, unique=True)

    # dimension
    floor_length = Column(Numeric)
    floor_width = Column(Numeric)
    floor_height = Column(Numeric, default=0)
    floor_offset_x = Column(Numeric, default=0)
    floor_offset_y = Column(Numeric, default=0)
    floor_unit = Column(String, default="FEET")

    # image
    image_name = Column(String)
    image_zoom_level = Column(Integer)
    image_width = Column(Numeric)
    image_height = Column(Numeric)
    image_size = Column(Numeric)
    image_max_resolution = Column(Numeric)
    image_color_depth = Column(Numeric)

    map_path = Column(String)

    zones = relationship("Zone", back_populates="floor", cascade="all, delete-orphan", lazy='dynamic')

    def __init__(self, building_id, aes_uid, calibration_model_id, object_version, name, floor_length, floor_width,
                 floor_height, floor_offset_x, floor_offset_y, floor_unit, image_name, image_zoom_level, image_width,
                 image_height, image_size, image_max_resolution, image_color_depth, zones=None, map_path=None):
        self.building_id = building_id
        self.aes_uid = aes_uid
        self.calibration_model_id = calibration_model_id
        self.object_version = object_version
        self.name = name
        self.floor_length = floor_length
        self.floor_width = floor_width
        self.floor_height = floor_height
        self.floor_offset_x = floor_offset_x
        self.floor_offset_y = floor_offset_y
        self.floor_unit = floor_unit
        self.image_name = image_name
        self.image_zoom_level = image_zoom_level
        self.image_width = image_width
        self.image_height = image_height
        self.image_size = image_size
        self.image_max_resolution = image_max_resolution
        self.image_color_depth = image_color_depth
        if zones:
            self.zones = zones
        self.map_path = map_path

    def __repr__(self):
        return "{}".format(self.name)

    def get_hierarchy(self):
        return "{}>{}".format(self.building.get_hierarchy(), self.name)


class Zone(Base):
    __tablename__ = "zone"
    floor_id = Column(BigInteger, ForeignKey('floor.aes_uid', ondelete='cascade'))
    floor = relationship("Floor", back_populates="zones")
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String, unique=True)
    zone_type = Column(String, default="ZONE")

    def __init__(self, floor_id, name, zone_type):
        self.floor_id = floor_id
        self.name = name
        self.zone_type = zone_type

    def __repr__(self):
        return "{}".format(self.name)

    def get_hierarchy(self):
        return "{}>{}".format(self.floor.get_hierarchy(), self.name)


class DeviceLocation(Base):
    __tablename__ = "device_location"
    id = Column(Integer, primary_key=True, unique=True)
    mac_address = Column(String, unique=True)
    coord_x = Column(Numeric, default=0)
    coord_y = Column(Numeric, default=0)
    last_modified = Column(DateTime(timezone=True))
    hierarchy = Column(String, nullable=False)

    def __init__(self, mac_address, hierarchy, last_modified, coord_x=0, coord_y=0):
        self.mac_address = mac_address
        self.hierarchy = hierarchy
        self.last_modified = last_modified
        self.coord_x = coord_x
        self.coord_y = coord_y

    def __repr__(self):
        return "{} is at {} @ {}".format(self.mac_address, self.hierarchy, self.last_modified)

    def to_json(self):
        item = {

            'mac_address': self.mac_address,
            'hierarchy': self.hierarchy,
            'coord_x': str(self.coord_x),
            'coord_y': str(self.coord_y),
            'last_modified': str(self.last_modified)
        }
        return item




class DeviceLocationHistory(Base):
    __tablename__ = "device_location_history"
    id = Column(Integer, primary_key=True, unique=True)
    mac_address = Column(String, unique=True)
    coord_x = Column(Numeric, default=0)
    coord_y = Column(Numeric, default=0)
    last_modified = Column(DateTime(timezone=True))
    hierarchy = Column(String, nullable=False)

    def __init__(self, mac_address, hierarchy, last_modified, coord_x=0, coord_y=0):
        self.mac_address = mac_address
        self.hierarchy = hierarchy
        self.last_modified = last_modified
        self.coord_x = coord_x
        self.coord_y = coord_y

    def __repr__(self):
        return "{} was at {} @ {}".format(self.mac_address, self.hierarchy, self.last_modified)

    def serialize(self):
        item = {

            'mac_address': self.mac_address,
            'hierarchy': self.hierarchy,
            'coord_x': str(self.coord_x),
            'coord_y': str(self.coord_y),
            'last_modified': str(self.last_modified)
        }
        return item



class EngagementTrigger (Base):
    __tablename__ = "engagement_trigger"
    id = Column(Integer, primary_key=True, unique=True)
    platform = Column(String, nullable=False)
    target = Column(String, nullable=False)
    value = Column(String, nullable=False)
    event = Column(String, nullable=False)
    zone_id = Column(Integer, ForeignKey('zone.id'))
    zone = relationship("Zone", backref="triggers")
    # TODO when the user is deleted, the engagement trigger row is not deleted.
    registered_user_id = Column(Integer, ForeignKey('registered_user.id', ondelete='cascade'))
    registered_user = relationship("RegisteredUser", backref="triggers")
    extras = Column(String, nullable=True)

    def __init__(self, platform, target, value, event, zone_id, registered_user_id, extras=None):
        self.platform = platform
        self.target = target
        self.value = value
        self.event = event
        self.zone_id = zone_id
        self.registered_user_id = registered_user_id
        if extras:
            self.extras = extras

    def __repr__(self):
        return '{} triggers {} for user.id = {} @ zone.id = {}'.format(self.event, self.platform, self.registered_user_id, self.zone_id)

    def serialize(self):
        item = {
            'id': self.id,
            'platform': self.platform,
            'target': self.target,
            'event': self.event,
            'zone_id': self.zone_id,
            'registered_user_id': self.registered_user_id,
            'extras': self.extras
        }
        return item

"""

class EngagementTrigger(Base):
    __tablename__ = "engagement_trigger"
    id = Column(Integer, primary_key=True, unique=True)
    mac_address = Column(String, nullable=False)
    hierarchy = Column(String, nullable=False)

"""