from django.conf.urls import url
from . import views
from . import feeds

urlpatterns = [
    url(r'^home$', views.home, name='home'),
    url(r'^resource/(?P<resource_id>\w+)', views.resource, name='resource'),
    url(r'^addResource$', views.addResource, name='addResource'),
    url(r'^editResource$', views.editResource, name='editResource'),
    url(r'^search$', views.search, name="search"),
    url(r'^tag/(?P<tagname>\w+)', views.tag, name='tag'),
    url(r'^reserve$', views.reserve, name='reserve'),
    url(r'^reservation/(?P<reservation_id>\w+)', views.reservation, name='reservation'),
    url(r'^delete_reservation/(?P<reservation_id>\w+)', views.delete_reservation, name='delete_reservation'),
    url(r'^register$', views.register, name='register'),
    url(r'^user/(?P<user_id>\w+)', views.user, name='user'),
    url(r'^login$', views.login, name="login"),
    url(r'^logout$', views.logout, name="logout"),
    url(r'^feeds/(?P<resource_id>\w+)', feeds.ReservationFeeds()),
    url(r'^image/(?P<resource_id>\w+)', views.image, name="image"),
    url(r'^$', views.home, name="home"),
]