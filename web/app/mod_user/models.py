from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base


class RegisteredUser(Base):
    __tablename__ = "registered_user"
    id = Column(Integer, primary_key=True, unique=True)
    mac_address = Column(String, unique=True)
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
            "name": self.name,
            "phone": self.phone,
            "mac_address": self.mac_address,
            "id": self.id
        }
        return out
