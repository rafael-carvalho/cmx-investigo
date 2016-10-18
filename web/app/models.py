from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.sql.sqltypes import Numeric, DateTime

from app.database import Base


class CMXServer(Base):
    __tablename__ = 'cmx_server'
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String, unique=True)
    url = Column(String, unique=True)
    username = Column(String)
    password = Column(String)
    externally_accessible = Column(Boolean)

    def __init__(self, name, url, username, password, externally_accessible):
        self.name = name
        self.url = url
        self.username = username
        self.password = password
        self.externally_accessible = externally_accessible

    def __repr__(self):
        return "{} ({})".format(self.name, self.url)


class DeviceLocation(Base):
    __tablename__ = "device_location"
    id = Column(Integer, primary_key=True, unique=True)
    mac_address = Column(String, unique=True)
    hierarchy = Column(String)
    coord_x = Column(Numeric, default=0)
    coord_y = Column(Numeric, default=0)
    last_modified = Column(DateTime(timezone=True))

    def __init__(self, mac_address, hierarchy, last_modified, coord_x=0, coord_y=0):
        self.mac_address = mac_address
        self.hierarchy = hierarchy
        self.last_modified = last_modified
        self.coord_x = coord_x
        self.coord_y = coord_y

    def __repr__(self):
        return "{} is at {} @ {}".format(self.mac_address, self.hierarchy, self.last_modified)
