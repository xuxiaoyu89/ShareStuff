from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from gaesessions import get_current_session
from django.contrib.sessions.backends.db import SessionStore
from google.appengine.ext import db
import models
import datetime
import forms
import helper
import os

'''
home view, display the following:
  user info,
  all the reservations by this user (sorted by the reserve time)
  all the resources in the system (sorted by the latest reserve time)
  all the resources owned by this user
  a link to add new resources
'''
def home(request):
    if not helper.Helper().isLoggedin(request):
        return redirect('login')
    session = get_current_session()
    email = request.session.data.keys()[0]
    name = session[email].name
    # get all the resources
    q = models.Resource.all()
    results = q.run()
    ids = []
    resources_with_ID = []
    myresources_with_ID = []
    for resource in results:
        # get all the reservations of this resource.
        curr_rsvs = db.GqlQuery(
            "SELECT * FROM Reservation where resource= :1", 
            str(resource.key().id_or_name())).run()
        latest = datetime.datetime(1,1,1,1,1,1)
        # get the latest reservation time
        for rsv in curr_rsvs:
            if rsv.reservetime > latest:
                latest = rsv.reservetime
        resources_with_ID.append([resource.key().id_or_name(), resource, latest])
        if resource.owner == email:
            myresources_with_ID.append([resource.key().id_or_name(), resource])
    # sort according to the latest reservation time
    resources_with_ID.sort(key=lambda x: x[2], reverse=True)
    for temp in resources_with_ID:
        if temp[2] == datetime.datetime(1,1,1,1,1,1):
            temp[2] = 'not reserved'
    q = db.GqlQuery("SELECT * FROM Reservation where user= :1", email)
    reservations = q.run()
    reservations_with_ID = []
    for reservation in reservations:
        # not show dated reservations
        curr_time = datetime.datetime.now() - datetime.timedelta(hours=5)
        et = reservation.starttime + datetime.timedelta(hours=reservation.duration)
        if curr_time > et:
            continue
        # get the resource name of this reservation
        q = db.GqlQuery(
            "SELECT * FROM Resource where __key__ = KEY('Resource', :1)", 
            int(reservation.resource))
        resource = q.get()
        reservations_with_ID.append(
            [reservation.key().id_or_name(), 
            resource.name, 
            reservation.reservetime])
    reservations_with_ID.sort(key=lambda x: x[2], reverse = True)

    return render_to_response('user.html', {
        'loggedin': True,
        'self_flag': True,
        'name': name, 
        'resources': resources_with_ID,
        'myresources': myresources_with_ID, 
        'reservations': reservations_with_ID})

'''
resource view, display the following:
  resource info: name, owner, avaiable time, rss link
  all the upcomming and current reservations 
  form to edit this Resource (if logged in and is the owner)
  form to add a reservations (if not the owner)
'''
def resource(request, resource_id):
    # test if logged in
    loggedin = False
    if helper.Helper().isLoggedin(request):
        loggedin = True
    # show upcomming reservations
    # get the current time
    q = db.GqlQuery("SELECT * FROM Reservation where resource= :1", resource_id)
    results = q.run()
    # show the reservation time and user
    # pack (reservartion_ID, username, reservation)
    reservations_with_info = []
    for reservation in results:
        # not show dated reservations
        curr_time = datetime.datetime.now() - datetime.timedelta(hours=5)
        et = reservation.starttime + datetime.timedelta(hours=reservation.duration)
        if curr_time > et:
            continue
        user = reservation.user
        username = db.GqlQuery("SELECT * FROM User where email = :1", user).get().name
        reservations_with_info.append((reservation.key().id_or_name(), username, reservation))

    user = '*'
    session = get_current_session()
    skeys = request.session.data.keys()
    isOwner = False
    if session.is_active() and skeys and session.has_key(skeys[0]):
        user = skeys[0]
    context = RequestContext(request)
    q = db.GqlQuery(
        "SELECT * FROM Resource where __key__ = KEY('Resource', :1)", 
        int(resource_id))
    resource = q.get()
    if resource.owner == user:
        isOwner = True # the resource is owned by the current user, so we can show the edit form to the user
    # get owner of this resource
    owner = db.GqlQuery("SELECT * FROM User where email = :1", resource.owner).get()
    owner_id = owner.key().id_or_name()
    owner_name = owner.name
    #image of this resource
    hasimage = False
    if resource.image:
        hasimage = True
    reserve_form = forms.ReserveForm(
        initial={
        'user': user, 
        'resource_id':resource_id})
    edit_form = forms.ResourceForm(
        initial={
        'resource_id': resource_id, 
        'name': resource.name, 
        'description':resource.description, 
        'tags': helper.Helper().tagstr(resource.tags), 
        'starttime': resource.starttime.strftime("%I:%M %p"), 
        'endtime': resource.endtime.strftime("%I:%M %p")})
    return render_to_response('resource.html', {
        'loggedin': loggedin,
        'owner_id': owner_id,
        'owner_name': owner_name,
        'resource': resource,
        'resource_id': resource_id,
        'hasimage':hasimage,
        'reservations': reservations_with_info, 
        'reserve_form': reserve_form, 
        'edit_form': edit_form,
        'isOwner': isOwner
        }, context)

'''
return the image of the resource
'''
def image(request, resource_id):
    resource = db.GqlQuery(
        "SELECT * FROM Resource where __key__ = KEY('Resource', :1)", 
        int(resource_id)).get()
    if resource and resource.image:
        return HttpResponse(resource.image, content_type="image/jpeg")

'''
collect info from the addResource form
create and save a resource
'''
def addResource(request):
    loggedin = True
    if not helper.Helper().isLoggedin(request):
        return redirect('login')
    email = request.session.data.keys()[0]
    context = RequestContext(request)
    if request.method == 'POST':
        form = forms.ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            # save the resource to db
            nm = form.cleaned_data['name']
            descr = form.cleaned_data['description']
            tgs = form.cleaned_data['tags'].split()
            currdate = datetime.date.today()
            st = datetime.datetime.combine(currdate, form.cleaned_data['starttime'])
            et = datetime.datetime.combine(currdate, form.cleaned_data['endtime'])
            imgblob = None
            img = None
            if 'image' in request.FILES:
                img = request.FILES['image']
                imgblob = db.Blob(img.read())
            # save the resource
            resource = models.Resource(
                owner=email, 
                name=nm, 
                description=descr, 
                image=imgblob, 
                tags=tgs, 
                postdate=currdate, 
                starttime=st, 
                endtime=et)
            resource.put()
            return redirect('home')    
        else:
            message = form.errors
            form = forms.ResourceForm(initial={
                'resource_id': 0000,})
            return render_to_response('addResource.html', 
                {
                'message': message,
                'loggedin': loggedin,
                'form': form
                }, context)
    else:
        form = forms.ResourceForm(initial={'resource_id': 0000})
    return render_to_response('addResource.html', 
        {
        'loggedin': loggedin,
        'form': form
        }, context)

'''
collect info from the editResource form
save the resource
'''
def editResource(request):
    if not helper.Helper().isLoggedin(request):
        return redirect('login')
    email = request.session.data.keys()[0]
    context = RequestContext(request)
    if request.method == 'POST':
        form = forms.ResourceForm(request.POST)
        if form.is_valid():
            r_id = form.cleaned_data['resource_id']
            nm = form.cleaned_data['name']
            descr = form.cleaned_data['description']
            tgs = form.cleaned_data['tags'].split()
            currdate = datetime.date.today()
            st = datetime.datetime.combine(currdate, form.cleaned_data['starttime'])
            et = datetime.datetime.combine(currdate, form.cleaned_data['endtime'])
            imgblob = None
            if 'image' in request.FILES:
                img = request.FILES['image']
                imgblob = db.Blob(img.read())
            # get the resource from database
            k = db.Key.from_path('Resource', int(r_id))
            resource = db.get(k)
            #resource.delete()
            #return redirect('home')
            # resource = models.Resource.get_by_id(r_id)
            if resource.owner != email:
                return redirect('home')
            resource.name = nm
            resource.description = descr
            resource.tags = tgs
            resource.starttime = st
            resource.endtime = et
            resource.image = imgblob
            resource.put()
            return redirect('home')

    return redirect('home')

'''
search by name or time
showing the results after searching
'''
def search(request):
    loggedin = True
    if not helper.Helper().isLoggedin(request):
        loggedin = False
    context = RequestContext(request)
    # if it have post request, then validate the form, and redirect the user accordingly
    if request.method == 'POST':
        form = forms.SearchForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            time = form.cleaned_data['time']
            duration = form.cleaned_data['duration']
            query = ''
            # search by name
            if name != '':
                query = "name: " + name
                resources = db.GqlQuery("SELECT * FROM Resource where name = :1", name).run()
                # wrap resources with ID, starttime
                resources_with_ID = []
                for resource in resources:
                    resources_with_ID.append([resource.key().id_or_name(), resource])
                return render_to_response('search.html', 
                    {'loggedin': loggedin,
                    'form':form, 
                    'resources':resources_with_ID,
                    'searched': True,
                    'query': query}, context)
            # search by time
            else:
                #verify input
                if time == None or duration == None:
                    return render_to_response("search.html", 
                    {'loggedin':loggedin,
                    'form': form,
                    'searched': False,
                    'query': query}, context) # message!!!
                curr_date = helper.Helper().getcurrdate()
                curr_time = datetime.datetime.now()
                st = datetime.datetime.combine(curr_date, time)
                et = st + datetime.timedelta(hours=duration)
                query = 'starttime: ' + st.strftime("%I:%M %p") + ', duration: ' + str(duration) + " hour(s)"
                # filter out some resources first, don't want to return all resources
                # resources = models.Resource.all().filter("endtime >=", et).run()
                resources = models.Resource.all().run()
                # wrap resources with ID, starttime
                for resource in resources:
                    if helper.Helper().isAvailable(resource.key().id_or_name(), st, duration, curr_time):   
                        resources_with_ID.append([resource.key().id_or_name(), resource])
                return render_to_response('search.html', 
                    {'loggedin': loggedin,
                    'form':form, 
                    'searched': True, 
                    'resources':resources_with_ID,
                    'query': query}, context)
        else:
            message = form.errors
            form = forms.SearchForm()
            return render_to_response('search.html', 
                {'loggedin': loggedin,
                'form': form, 
                'searched': False}, context)

    else:
        form = forms.SearchForm()
    return render_to_response('search.html', 
        {'loggedin': loggedin,
        'form': form, 
        'searched': False}, context)

'''
show all the resources with this tag
'''
def tag(request, tagname):
    loggedin = True
    if not helper.Helper().isLoggedin(request):
        loggedin = False
    # get all the resources
    q = models.Resource.all()
    results = q.run()
    resources_with_ID = []
    for resource in results:
        if tagname in resource.tags:
            resources_with_ID.append((resource.key().id_or_name(), resource))
    return render_to_response('tag.html', 
        {'loggedin': loggedin,
        'resources': resources_with_ID, 
        'tagname': tagname})

'''
reserve the resource
'''
def reserve(request):
    # check if the time is ok
    context = RequestContext(request)
    if request.method == 'POST':
        form = forms.ReserveForm(request.POST)
        if form.is_valid():
            # save to database
            # print "user name: ", form.cleaned_data['username']
            currdate = datetime.date.today()
            usr = form.cleaned_data['user']
            r_id = form.cleaned_data['resource_id']
            st = datetime.datetime.combine(currdate, form.cleaned_data['starttime'])
            dur = form.cleaned_data['duration']
            # user not logged in
            if usr == '*':
                return redirect('login')
            # check if there is other reservations in this time
            # get the current time
            curr_time = datetime.datetime.now()

            if helper.Helper().isAvailable(r_id, st, dur, curr_time):
                reserve = models.Reservation(
                    user=usr, 
                    resource=r_id, 
                    starttime=st, 
                    duration=dur, 
                    reservetime=curr_time)
                reserve.put()
                return redirect('home')
            else:
                q = db.GqlQuery(
                    "SELECT * FROM Resource where __key__ = KEY('Resource', :1)", 
                    int(r_id))
                resource = q.get()
                reserve_form = forms.ReserveForm(
                    initial={
                    'user': usr, 
                    'resource_id':r_id, 
                    'starttime':st.strftime("%I:%M %p"), 
                    'duration':dur})
                message = 'Sorry, this resource is reserved in this time slot.'
                return render_to_response('resource.html', {
                    'loggedin': True,
                    'resource': resource, 
                    'reserve_form': reserve_form, 
                    'message': message}, context)
        else:
            html = "<html><body>ID: %s.</body></html>" % form.errors
            return HttpResponse(html)
    return redirect('home')

'''
show the info of this reservation:
user name, resource name, and reservation starttime and duration
'''
def reservation(request, reservation_id):
    loggedin = True
    if not helper.Helper().isLoggedin(request):
        loggedin = False

    context = RequestContext(request)
    q = db.GqlQuery(
        "SELECT * FROM Reservation where __key__ = KEY('Reservation', :1)", 
        int(reservation_id))
    reservation = q.get()
    # show the user, resource name, reservation time and duration
    # get the user name and id
    email = reservation.user
    user= db.GqlQuery("SELECT * FROM User where email= :1", email).get()
    user_id = user.key().id_or_name()
    user_name = user.name

    # get the resource name
    resource = db.GqlQuery(
        "SELECT * FROM Resource where __key__ = KEY('Resource', :1)", 
        int(reservation.resource)).get()
    resource_name = resource.name
    resource_id = reservation.resource
    return render_to_response('reservation.html', {
        'loggedin': loggedin,
        'reservation': reservation,
        'user_id': user_id,
        'user_name': user_name,
        'resource_name': resource_name,
        'resource_id': resource_id,
        }, context)

'''
delete the reservation given reservation_id
'''
def delete_reservation(request, reservation_id):
    if not helper.Helper().isLoggedin(request):
        return redirect('login')
    email = request.session.data.keys()[0]
    # get the reservation
    k = db.Key.from_path('Reservation', int(reservation_id))
    reservation = db.get(k)
    if reservation.user == email:
        reservation.delete()
    return redirect('home')

'''
user register: given name, email and password
validate the email (if it is valid and whether exists in the database)
'''
def register(request):
    context = RequestContext(request)
    if request.method == 'POST':
        form = forms.RegisterForm(request.POST)
        if form.is_valid():
            # save to database
            # print "user name: ", form.cleaned_data['username']
            pw = form.cleaned_data['password']
            eml = form.cleaned_data['email']
            usr = form.cleaned_data['name']
            # check if email is valid
            if '@' not in eml:
                return render_to_response(
                    'register.html', 
                    {'loggedin': False,
                    'form': form, 
                    'message': 'the email is not valid'}, context)
            # check if email already exists
            q = db.GqlQuery("SELECT * FROM User " +
                "WHERE email = :1", eml)
            result = q.get()
            if result:
                return render_to_response(
                    'register.html', 
                    {'loggedin': False,
                    'form': form, 
                    'message': 'the email already exists'}, context)
            user = models.User(email=eml, password=pw, name=usr)
            user.put()
            # show the user the home page
            session = get_current_session()
            session[eml] = user
            session.save()
            return redirect('home')
        else:
            html = "<html><body>ID: %s.</body></html>" % form.errors
            return HttpResponse(html)
    else:
        form = forms.RegisterForm()
    return render_to_response('register.html', 
        {'loggedin': False,
        'form': form}, context)

'''
login the user
render all the resources in the system
'''
def login(request):
    # first get all the resources in the system
    q = models.Resource.all()
    results = q.run()
    resources_with_ID = []
    for resource in results:
        resources_with_ID.append((resource.key().id_or_name(), resource))
    # test if logged in
    session = get_current_session()
    if session.is_active():
        if request.session.data.keys():
            email = request.session.data.keys()[0]
            if session.has_key(email):
                return redirect('home')
    context = RequestContext(request)

    # if it have post request, then validate the form, and redirect the user accordingly
    if request.method == 'POST':
        form = forms.LoginForm(request.POST)
        if form.is_valid():
            # save to database
            pw = form.cleaned_data['password']
            eml = form.cleaned_data['email']
            message = ''
            q = db.GqlQuery("SELECT * FROM User " +
                "WHERE email = :1", eml)
            usr = q.get()
            if usr == None:
                # error message
                message = 'the email you entered does not exist'
                return render_to_response('login.html', {
                    'form': form, 
                    'resources': resources_with_ID,
                    'message': message}, context)
            if usr.password != pw:
                # error message
                message = 'the password does not match'
                return render_to_response('login.html', {
                    'form': form, 
                    'resources': resources_with_ID,
                    'message': message}, context)
            # show the user the home page
            session = get_current_session()
            session[eml] = usr
            session.save()
            # html = "<html><body>ID: %s.</body></html>" % usr.key().id_or_name()
            # return HttpResponse(html)
            return redirect('home')
        else:
            # print in the terminal
            html = "<html><body>ID: %s.</body></html>" % form.errors
            return HttpResponse(html)
    else:
        form = forms.LoginForm()
    return render_to_response('login.html', {
        'loggedin': False,
        'form': form, 
        'resources': resources_with_ID}, context)
    #return render(request, 'login.html', {'form': form})

'''
given user_id, render info of this user:
name and email,
all the resources he owns
all the reservations he has (not dated)
'''
def user(request, user_id):
    loggedin = True
    if not helper.Helper().isLoggedin(request):
        loggedin = False
    user = resource = db.GqlQuery(
        "SELECT * FROM User where __key__ = KEY('User', :1)", 
        int(user_id)).get()
    # get all the resources
    q = models.Resource.all()
    results = q.run()
    ids = []
    resources_with_ID = []
    myresources_with_ID = []
    for resource in results:
        #resources_with_ID.append((resource.key().id_or_name(), resource))
        if resource.owner == user.email:
            myresources_with_ID.append((resource.key().id_or_name(), resource))

    q = db.GqlQuery("SELECT * FROM Reservation where user= :1", user.email)
    reservations = q.run()
    reservations_with_ID = []
    for reservation in reservations:
        # not show dated reservations
        curr_time = datetime.datetime.now() - datetime.timedelta(hours=5)
        et = reservation.starttime + datetime.timedelta(hours=reservation.duration)
        if curr_time > et:
            continue
        # get the resource name of this reservation
        q = db.GqlQuery(
            "SELECT * FROM Resource where __key__ = KEY('Resource', :1)", 
            int(reservation.resource))
        resource = q.get()
        reservations_with_ID.append((
            reservation.key().id_or_name(), 
            resource.name, 
            resource.starttime))

    return render_to_response('user.html', {
        'loggedin': loggedin,
        'self_flag': False,
        'name': user.name, 
        'email': user.email,
        'resources': resources_with_ID,
        'myresources': myresources_with_ID, 
        'reservations': reservations_with_ID})

'''
logout the user
'''
def logout(request):
    session = get_current_session()
    if session.is_active():
        if request.session.data.keys():
            email = request.session.data.keys()[0]
            if session.has_key(email):
                del session[email]
    return redirect('login')






































