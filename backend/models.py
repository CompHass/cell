from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Group(Base):
    __tablename__ = "groups"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)

class Person(Base):
    __tablename__ = "persons"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    group_id = Column(String, index=True)
    is_member = Column(Boolean, nullable=False, default=True, server_default="true")

class Event(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True)
    date = Column(DateTime)
    name = Column(String)
    group_id = Column(String, index=True)

class Attendance(Base):
    __tablename__ = "attendance"
    event_id = Column(String, primary_key=True)
    person_id = Column(String, primary_key=True)
    status = Column(String)
    group_id = Column(String, index=True)
