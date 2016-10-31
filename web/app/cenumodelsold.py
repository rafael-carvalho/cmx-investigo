'''
Created on Jul 27, 2016

@author: rafacarv
'''
#http://flask-sqlalchemy.pocoo.org/2.1/models/
#https://realpython.com/blog/python/flask-by-example-part-2-postgres-sqlalchemy-and-alembic/
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import Numeric, BigInteger


Base = declarative_base()

class User (Base):
    __tablename__ = "user"
    mac_address = Column(String, primary_key=True, unique=True)
    name = Column(String)
    phone = Column(String)
    
    def __init__(self, name, mac_address, phone=None):
        self.name = name
        self.mac_address = mac_address
        self.phone = phone
        
    def __repr__(self):
        return "{} ({})".format(self.name, self.mac_address)
    
    def serialize(self):
        out = {
               "name" : self.name,
               "phone" : self.phone,
               "mac_address" : self.mac_address
               }
        return out

class System (Base):
    __tablename__ = "system"
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String, unique=True)
    url = Column(String, unique=True)
    username = Column(String)
    password = Column(String)
    
    def __init__(self, name, url, username, password):
        self.name = name
        self.url = url
        self.username = username
        self.password = password

class Campus (Base):
    __tablename__ = "campus"
    aesUid = Column (BigInteger, primary_key=True, unique=True)
    name = Column(String, unique=True)
    buildings = relationship ("Building", cascade="all, delete-orphan", lazy='dynamic')
    fakeName = Column(String)
    
    def __init__(self, aesUid, name, buildings=None):
        self.aesUid = aesUid
        self.name = name
        if (buildings is not None):
            self.buildings = buildings

        
    def __repr__(self):
        return "{}".format(self.name)
    
    def getHierarchy(self):
        return self.name
    
    def getFakeHierarchy(self):
        return self.fakeName
    
class Building (Base):
    __tablename__ = "building"
    aesUid = Column (BigInteger, primary_key=True, unique=True)
    objectVersion = Column (Integer, default=0)
    name = Column (String, unique=True)
    campus_id = Column(BigInteger, ForeignKey('campus.aesUid', ondelete='cascade'))
    campus = relationship("Campus", back_populates="buildings")
    floors = relationship ("Floor", cascade="all, delete-orphan", lazy='dynamic')
    fakeName = Column(String)
    
    def __init__(self, campus_id, aesUid, objectVersion, name, floors=None):
        self.aesUid = aesUid
        self.objectVersion = objectVersion
        self.name = name
        self.campus_id = campus_id
        if (floors is not None):
            self.floors = floors
    
    def __repr__(self):
        return "{}".format(self.name)
    
    def getHierarchy(self):
        return "{}>{}".format(self.campus.getHierarchy(), self.name)
    
    def getFakeHierarchy(self):
         return "{}>{}".format(self.campus.getFakeHierarchy(), self.fakeName)
    
class Floor (Base):
    __tablename__ = "floor"
    building_id = Column(BigInteger, ForeignKey('building.aesUid', ondelete='cascade'))
    building = relationship("Building", back_populates="floors")
    aesUid = Column (BigInteger, primary_key=True, unique=True)
    calibrationModelId = Column (BigInteger)
    objectVersion = Column (Integer, default=0)
    name = Column (String, unique=True)
    fakeName = Column(String)
    
    #dimension
    floor_length = Column (Numeric)
    floor_width = Column (Numeric)
    floor_height = Column (Numeric, default=0)
    floor_offsetX = Column (Numeric, default=0)
    floor_offsetY = Column (Numeric, default=0)
    floor_unit = Column (String, default="FEET")
    
    #image
    image_name = Column (String)
    image_zoom_level = Column (Integer)
    image_width = Column (Numeric)
    image_height = Column (Numeric)
    image_size = Column (Numeric)
    image_max_resolution = Column (Numeric)
    image_color_depth = Column (Numeric)

    zones = relationship("Zone", back_populates="floor", cascade="all, delete-orphan", lazy='dynamic')
    
    def __init__(self, building_id, aesUid, calibrationModelId, objectVersion, name, floor_length, floor_width, floor_height, floor_offsetX, floor_offsetY, floor_unit, image_name, image_zoom_level, image_width, image_height, image_size, image_max_resolution, image_color_depth, zones=None):
        self.building_id = building_id
        self.aesUid = aesUid
        self.calibrationModelId = calibrationModelId
        self.objectVersion = objectVersion
        self.name = name
        self.floor_length = floor_length
        self.floor_width = floor_width
        self.floor_height = floor_height
        self.floor_offsetX = floor_offsetX
        self.floor_offsetY = floor_offsetY
        self.floor_unit = floor_unit
        self.image_name = image_name
        self.image_zoom_level = image_zoom_level
        self.image_width = image_width
        self.image_height = image_height
        self.image_size = image_size
        self.image_max_resolution = image_max_resolution
        self.image_color_depth = image_color_depth
        
        if (zones is not None):
            self.zones = zones
    
    def __repr__(self):
        return "{}".format(self.name)
    
    def getHierarchy(self):
        return "{}>{}".format(self.building.getHierarchy(), self.name)
    
    def getFakeHierarchy(self):
         return "{}>{}".format(self.building.getFakeHierarchy(), self.fakeName)
    
class Zone (Base):
    __tablename__ = "zone"
    floor_id = Column(BigInteger, ForeignKey('floor.aesUid', ondelete='cascade'))
    floor = relationship("Floor", back_populates="zones")
    id = Column(Integer, primary_key=True, unique=True)
    name = Column (String, unique=True)
    zone_type = Column (String, default="ZONE")
    occupancy = relationship("Occupancy", uselist=False, back_populates="zone") #One to One relationship
    #agents = relationship("Agent", back_populates="zone", lazy='dynamic') #One to Many relationship
    agents = relationship("AgentsZone", back_populates="zone", lazy='dynamic')
    fakeName = Column(String)
    
    def __init__(self, floor_id, name, zone_type):
        self.floor_id = floor_id
        self.name = name
        self.zone_type = zone_type
    
    def __repr__(self):
        return "{}".format(self.name)
    
    def getHierarchy(self):
        return "{}>{}".format(self.floor.getHierarchy(), self.name)
        
    def getFakeHierarchy(self):
         return "{}>{}".format(self.floor.getFakeHierarchy(), self.fakeName)
     
class Occupancy (Base):    
    __tablename__ = "occupancy"
    id = Column(Integer, primary_key=True, unique=True)
    threshold_devices = Column(Numeric, default=0)
    threshold_users = Column(Numeric, default=0)
    zone_id = Column(Integer, ForeignKey('zone.id'))
    zone = relationship("Zone", back_populates="occupancy")

class Agent (Base):
    __tablename__ = "agent"
    id = Column(Integer, primary_key=True, unique=True)
    name = Column (String)
    specialization = Column (String)
    #zone_id = Column(BigInteger, ForeignKey('zone.id'))
    #zone = relationship("Zone", back_populates="agents")
    zone = relationship("AgentsZone", back_populates="agent", uselist=False)

    def __init__(self, name, specialization=None):
        self.name = name
        self.specialization = specialization

    def __repr__(self):
        return "{} ({})".format(self.name, self.specialization)


#Association Table http://docs.sqlalchemy.org/en/latest/orm/basic_relationships.html#association-object
class AgentsZone (Base):
    __tablename__ = "agents_zone"
    zone_id = Column(Integer, ForeignKey('zone.id', ondelete='cascade'), primary_key=True)
    agent_id = Column(Integer, ForeignKey('agent.id', ondelete='cascade'), primary_key=True)
    extra_data = Column(String(50))
    zone = relationship("Zone", backref="zone_associations")
    agent = relationship("Agent", backref="agent_associations")

    def __init__(self, extra_data=None):
        self.extra_data = extra_data
        

class MACTrack (Base):
    __tablename__ = "mactrack"
    mac_address = Column(String, primary_key=True, unique=True)
    hierarchy = Column(String)
    coord_x = Column (Numeric, default=0)
    coord_y = Column (Numeric, default=0)
    last_modified = Column(DateTime(timezone=True))

    def __init__(self, mac_address, hierarchy, last_modified, coord_x=0, coord_y=0):
        self.mac_address = mac_address
        self.hierarchy = hierarchy
        self.last_modified = last_modified
        self.coord_x = coord_x
        self.coord_y = coord_y

    def __repr__(self):
        return "{} is at {} @ {}".format(self.mac_address, self.hierarchy, self.last_modified)