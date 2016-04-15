import datetime
from google.appengine.ext import db
from gaesessions import get_current_session

class Helper():
    '''
    get the current date in New York
    now().time() is UTC, 5 hours ahead of us
    '''
    def getcurrdate(self):
        curr_time = datetime.datetime.now().time()
        if curr_time > datetime.time(0,0,0,0) and curr_time < datetime.time(5,0,0,0):
            return datetime.date.today() - datetime.timedelta(days=1)
        else:
            return datetime.date.today()
    
    '''
    contatenate the tags list
    '''
    def tagstr(self, tags):
        result = ''
        for tag in tags:
            result += tag + ' '
        return result

    '''
    test if the resource is available in the given time period
    arguements:
      rid: resource id
      st: wanted start time
      dur: wanted duration
      curr_t: curr_time in UTC
    return:
      True if is available
      False if not available
    '''
    def isAvailable(self, rid, st, dur, curr_t):
        q = db.GqlQuery("SELECT * FROM Reservation where resource= :1", rid)
        reservations = q.run()
        q = db.GqlQuery("SELECT * FROM Resource where __key__ = KEY('Resource', :1)", int(rid))
        resource = q.get()
        rscst = resource.starttime
        rscet = resource.endtime
        # change curr_t form UDT to New York time
        curr_t = curr_t - datetime.timedelta(hours=5)
        # if the resource is dated
        if curr_t > rscet:
            #return [curr_t, rscet]
            # return [False, "outdated", rscst, rscet, rscst, rscet]
            return False
        currst = st
        curret = currst + datetime.timedelta(hours=dur)
        for reservation in reservations:
            tempst = reservation.starttime
            tempet = tempst + datetime.timedelta(hours=reservation.duration)
            if currst >= tempet or curret <= tempst:
                continue
            else: 
                #return [False, "have other reservations", rscst, rscet, currst, curret]
                return False
        # compare with the resource frame
        if currst >= rscst and curret <= rscet:
            #return [True, "isAvailable", rscst, rscet, currst, curret]
            return True
        # return [False, "not in the time frame of the resource", rscst, rscet, currst, curret]
        return False

    '''
    test if a user is logged in
    '''
    def isLoggedin(self, request):
        session = get_current_session()
        if not session.is_active():
            return False
        if not request.session.data.keys():
            return False
        email = request.session.data.keys()[0]
        if not session.has_key(email):
            return False
        #update the session
        session.save()
        return True


