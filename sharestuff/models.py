from django.db import models
from google.appengine.ext import db
from google.appengine.api import users


# Create your models here.
class User(db.Model):
    email       = db.StringProperty(required=True)
    password    = db.StringProperty(required=True)
    name        = db.StringProperty(required=True)

class Resource(db.Model):
    owner       = db.StringProperty(required=True)
    name        = db.StringProperty(required=True)
    description = db.StringProperty(required=False)
    image      = db.BlobProperty(required=False)
    tags        = db.StringListProperty(required=True)
    postdate    = db.DateProperty(required=True)
    starttime   = db.DateTimeProperty(required=True) 
    endtime     = db.DateTimeProperty(required=True)

class Reservation(db.Model):
    user        = db.StringProperty(required=True)      # email of user 
    resource    = db.StringProperty(required=True)      # id of resource
    reservetime = db.DateTimeProperty(required=True)    # time the reservation is made
    starttime   = db.DateTimeProperty(required=True)    # start time
    duration    = db.IntegerProperty(required=True)     # duration

