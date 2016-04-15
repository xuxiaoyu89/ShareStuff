from django.contrib.syndication.views import Feed
from models import User
from models import Resource
from models import Reservation
from google.appengine.ext import db

'''
Each resource will have an RSS link, 
that dumps all reservations for that resource in XML format
'''

class ReservationFeeds(Feed):
    title = "Resource Feeds"
    link = "www.xx450sharestuff.appspot.com"
    description = "Feeds for all Reservations of this resource"


    def get_object(self, request, resource_id):
        k = db.Key.from_path('Resource', int(resource_id))
        resource = db.get(k)
        return resource

    def items(self, obj):
        resource_id = obj.key().id_or_name()
        results = []
        temp = db.GqlQuery("SELECT * FROM Reservation where resource= :1", str(resource_id)).run()
        for t in temp:
            results.append(t)
        return results

    def item_title(self, obj):
        # get user
        return "reservation " + str(obj.key().id_or_name())

    def item_link(self, obj):
        return "www.xx450sharestuff.com/reservation/" + str(obj.key().id_or_name())

    def item_description(self, obj):
        description = ""
        user = db.GqlQuery("SELECT * FROM User where email= :1", obj.user).get()
        description += "reservation by " + user.name + "(" + user.email + "),"
        description += "reserved at " + obj.reservetime.strftime("%I:%M %p")
        return description





