from django.contrib import admin
from . import views
from django.conf.urls import include, url

from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView

urlpatterns = [
    url(r'djangoadmin/', admin.site.urls),
    url(r'^login', auth_views.login, {'template_name': 'adminlte/login.html'}, name='login'),
    url(r'^logout', auth_views.logout,  {'next_page': '/'}, name='logout'),
    url(r'^signup', views.signup, name='signup'),
    url(r'^api', views.api, name='problems_index'),
    url(r'^plugins', views.plugins, name='plugins_index'),
    url(r'^admin', views.admin, name='admin_index'),
    url(r'^player', views.player, name='player_index'),
    url(r'^channels', views.channels, name='channels_index'),
    url(r'^resources/(?P<path>.*)$', views.resources, name='get_resources'),
    url(r'^favicon\.ico$', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),
    url(r'^manifest\.json$', RedirectView.as_view(url='/static/manifest.json', permanent=True)),
    url(r'^browserconfig\.xml$', RedirectView.as_view(url='/static/browserconfig.xml', permanent=True)),
    url(r'^$', RedirectView.as_view(url='player', permanent=False), name='index')
    
]
