import json
import os
import time
import threading
import subprocess
import redis
import traceback
import random
import redis
from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils.http import http_date
from . import models
from django.db.models import Count
from django.contrib.sessions.models import Session
from django.utils import timezone
from .backgroundWorker import UpcomingLoader
from django import forms
from django.contrib.auth.forms import UserCreationForm
from kodino import kodino
from .stats import Stats
from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect

kodinoRoot = None # loaded in first api call
upcomingLoader = None # loaded in first api call
stats = None 

redis_connection = redis.StrictRedis(host='localhost', port=6379, db=4)


class SignUpForm(UserCreationForm):
    username = forms.CharField(max_length=100, required=True,help_text="")
    password2 = forms.CharField(max_length=100, required=True,help_text="",label="Password confirmation", widget=forms.PasswordInput())
    allowAdult = forms.BooleanField(label="Show adult content", required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', )
  


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            try:
                allowAdult = form.cleaned_data.get('allowAdult')
            except:
                allowAdult = False
            settings = models.UserSetting()
            settings.user = user
            settings.allowAdult = allowAdult
            settings.save()
            login(request, user)
            return redirect('channels_index')
        
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})
  
def channels(request,**kwargs):
    template = loader.get_template('channels.html')
    return HttpResponse(template.render({}, request))
 
def player(request,**kwargs):
    template = loader.get_template('player.html')
    return HttpResponse(template.render({}, request))
   
def admin(request,**kwargs):
    if request.user.is_superuser != True:
        return HttpResponse("You must be superuser")
    template = loader.get_template('admin.html')
    return HttpResponse(template.render({}, request))
   
def plugins(request,**kwargs):
    if request.user.is_superuser != True:
        return HttpResponse("You must be superuser")
    template = loader.get_template('plugins.html')
    return HttpResponse(template.render({}, request))
  
def resources(request, path):
    path = os.path.abspath("%s/%s" % (kodino.settings.PLUGINS_FOLDER, path))
    if not path.startswith(kodino.settings.PLUGINS_FOLDER) or not os.path.exists(path):
        r = HttpResponse('')
        r['Expires'] = http_date(time.time() + (3600 * 12))
        r['Cache-Control'] = 'public,max-age=%d' % (3600 * 12)
        return r
    filename = os.path.basename(path)
    f = open(path, 'rb')
    response = HttpResponse(content=f)
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    response['Expires'] = http_date(time.time() + (3600 * 12))
    response['Cache-Control'] = 'public,max-age=%d' % (3600 * 12)
    return response

def api(request):
    global upcomingLoader 
    if upcomingLoader == None:
        upcomingLoader = UpcomingLoader()
        upcomingLoader.start()
    global kodinoRoot 
    if kodinoRoot == None:
        kodinoRoot = kodino.Kodino()
    global stats 
    if stats == None:
        stats = Stats()
        stats.start()
         
    api = request.POST.get("api", "")
    
    try:
        request.user.settings
    except: 
        print("User %s has not settings, creating" % request.user.username)
        settings = models.UserSetting()
        settings.user = request.user
        settings.allowAdult = True;
        settings.save()
    
    if api == "admin":
        return _api_admin(request)
    
    if api == "browser":
        return _api_browser(request)

    if api == "channels":
        return _api_channels(request)

    if api == "globalExcludeFilters":
        return _api_globalExcludeFilters(request)

    if api == "plugins":
        return _api_plugins(request)
        
    if api == "stats":
        return _api_stats(request)
 
    if api == "upcoming":
        return _api_upcoming(request)
        
    return JsonResponse({'status':'ERROR',"message":"Unknown api '%s'" % api})
      

   
def _api_admin(request):
    if request.user.is_superuser != True:
        return JsonResponse({'status':'ERROR',"message":"You must be superuser"})
        
    command = request.POST.get("command", "")
    
    if command == "startLoader":
        upcomingLoader.start()
        return JsonResponse({'status':'OK'}) 
    
    if command == "stopLoader":
        upcomingLoader.stop()
        return JsonResponse({'status':'OK'})  
                    
    if command == "loaderStatus":
        return JsonResponse({'status':'OK', 'loader': upcomingLoader.toDict()})      
        
    if command == "addUser":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        email = request.POST.get("email", "")
        try:
            User.objects.get(username=username)
            return JsonResponse({'status':'ERROR',"message":"User exists"})
        except:
            pass
        try:
            User.objects.get(email=email)
            return JsonResponse({'status':'ERROR',"message":"User exists"})
        except:
            pass            
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        return JsonResponse({'status':'OK'})
        
    if command == "deleteUser":
        user_id = request.POST.get("user_id", "")
        user = User.objects.get(id=user_id)            
        if user.username == "admin":
            return JsonResponse({'status':'ERROR',"message":"Can't delete admin user"})
        user.delete()
        return JsonResponse({'status':'OK'})
        
    if command == "getUsers":
        users = User.objects.all()
        usersresult = []
        for u in users:
            usersresult.append({
                "id" : u.id,
                "username" : u.username,
                "email" : u.email,
                "last_login" : u.last_login,
                "allowAdult" : u.settings.allowAdult,
            })
        return JsonResponse({'status':'OK', 'users': usersresult})
    
    if command == "getOverview":        
        uid_list = [session.get_decoded().get('_auth_user_id', None) for session in Session.objects.filter(expire_date__gte=timezone.now())]
        r = {
            "count_users" : models.User.objects.count(),
            "count_users_loggedin" : models.User.objects.filter(id__in=uid_list).count(),
            "count_channels" : models.Channel.objects.count(),
            "count_upcoming" : models.Upcoming.objects.count(),
            "count_plugins_installed" : len(kodinoRoot.plugins.installed),
        }
        return JsonResponse({'status':'OK', 'data': r})
        
    if command == "getCacheStats":        
        cached_items_count = redis_connection.get("stats:cached_items")
        if cached_items_count != None:
            cached_items_count = int(cached_items_count)
        else:
            cached_items_count = 0
        r = {
            "cached_items" : cached_items_count
        }
        return JsonResponse({'status':'OK', 'data': r})
        
    if command == "getPlaybackStats":        
        return JsonResponse({'status':'OK', 'data': stats.get([[kodinoRoot.hash,""],]) })
        
    if command == "clearCache":
        keys = []
        for key in redis_connection.scan_iter(match="cache:*"):
            keys.append(key)
        pipe = redis_connection.pipeline()
        for key in keys:
            pipe.delete(key)
        pipe.execute()
        redis_connection.set("stats:cached_items",0)
        redis_connection.expire("stats:cached_items", 3600)
        return JsonResponse({'status':'OK'})
        
    if command == "clearStats":
        keys = []
        for key in redis_connection.scan_iter(match="stats:*"):
            keys.append(key)
        pipe = redis_connection.pipeline()
        for key in keys:
            pipe.delete(key)
        pipe.execute()
        return JsonResponse({'status':'OK'})
        
  
    if command == "recreateStats":        
        stats.create() 
        return JsonResponse({'status':'OK'})
               
     
    return JsonResponse({'status':'ERROR',"message":"Unknown command '%s'" % command})          
          
def _api_browser(request):
    command = request.POST.get("command", "")
    if command == "open":
        try:
            path = json.loads(request.POST.get("path", "[]"))
        except:
            return JsonResponse({'status':"error","message": "Failed to load item path"})
        item, items = kodinoRoot.resolveHashPath(path)
        items =  [i.toDict() for i in items]
        tmpitems = []
        usersettings = request.user.settings
        for i in items:
            i["thumbnailImage"] = i["thumbnailImage"].replace(kodino.settings.PLUGINS_FOLDER, "resources")
            i["stats"] = stats.get(i["path"])
            if i["isAdult"] == True and usersettings.allowAdult == False:
                continue
            tmpitems.append(i)
        items = tmpitems   
        item = item.toDict()
        item["stats"] = stats.get(item["path"])
        item["thumbnailImage"] = item["thumbnailImage"].replace(kodino.settings.PLUGINS_FOLDER, "resources")
        if item["isAdult"] == True and usersettings.allowAdult == False:
            item = None
        return JsonResponse({'status':'OK', 'item': item, 'items': items})  
        
    return JsonResponse({'status':'ERROR',"message":"Unknown command '%s'" % command})   
   
def _api_channels(request):
    command = request.POST.get("command", "")
    if command == "get":
        try:
            channels = models.Channel.objects.filter(owner = request.user)
        except:
            return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})
        return JsonResponse({'status':'OK', 'channels' : [c.toDict() for c in channels ]})
        
    if command == "create":
        try:
            channels_count = models.Channel.objects.filter(owner = request.user).count()
        except:
            return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})
        if channels_count > 50: 
            return  JsonResponse({'status':'ERROR', 'message' : "50 channels is enough"})
        channel = models.Channel()
        channel.name = "Channel %s" % (channels_count +1)
        channel.description = "This is Channel %s" % (channels_count +1)
        channel.index = channels_count + 1
        channel.owner = request.user
        channel.save()
        return JsonResponse({'status':'OK'})

    if command == "removeSource":
        try:
            channelsource = models.ChannelSource.objects.get(id=request.POST.get("source_id", ""))
        except:
            return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})

        if(channelsource.channel.owner != request.user):
            return JsonResponse({'status':'ERROR',"message":"You are not the owner of this source"})            
        channelsource.delete()
        return JsonResponse({'status':'OK'})          

    if command == "removeIncludeFilter":
        try:
            filter =  models.ChannelIncludeFilter.objects.get(id=request.POST.get("filter_id", ""))
        except:
            return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})

        if(filter.channel.owner != request.user):
            return JsonResponse({'status':'ERROR',"message":"You are not the owner of this filter"})
        filter.delete()
        filter.channel.upfill_errorcount = 0
        filter.channel.save(update_fields=["upfill_errorcount"])
        return JsonResponse({'status':'OK'})
      
    if command == "removeExcludeFilter":
        try:
            filter =  models.ChannelExcludeFilter.objects.get(id=request.POST.get("filter_id", ""))
        except:
            return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})

        if(filter.channel.owner != request.user):
            return JsonResponse({'status':'ERROR',"message":"You are not the owner of this filter"})
        filter.delete()
        filter.channel.upfill_errorcount = 0
        filter.channel.save(update_fields=["upfill_errorcount"])
        return JsonResponse({'status':'OK'})
      
    if command == "getCurrentVideo":
        channel_index = "%s"% request.POST.get("channel_index", "")
        print("request channel index %s" % channel_index)
        try:
            channel = models.Channel.objects.get(index=channel_index, owner = request.user)
        except Exception as e:
            print("Exception in views.py getCurrentVideo: %s" % e)
            return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})

        try:
            prevchannel = models.Channel.objects.get(index="%s"%(int(channel_index)-1), owner = request.user).toDict()
        except:
            prevchannel = {}
        try:
            nextchannel = models.Channel.objects.get(index="%s"%(int(channel_index)+1), owner = request.user).toDict()
        except:
            nextchannel = {}
            
        try:
            nrofchannels = models.Channel.objects.filter(owner = request.user).count()
        except:
            nrofchannels = 0       
            
        while True:    
            r = channel.get_current_video()
            if r != None:
                startposition, currentvideo = r
                playbackurl = currentvideo.getPlaybackUrl()
                if playbackurl == "":
                    currentvideo.delete()
                    continue
                channeldict = channel.toDict()
                currentvideo = currentvideo.toDict()
            else:
                startposition = 0
                playbackurl = ""
                currentvideo = {}
                channeldict = channel.toDict()
            break
            
        return JsonResponse({
            'status':'OK', 
            "startposition" : startposition, 
            "playbackurl": playbackurl, 
            "currentvideo": currentvideo,
            "prevchannel": prevchannel,
            "currentchannel": channeldict,
            "nextchannel": nextchannel,
            "nrofchannels" : nrofchannels,
        })      
      
    if command == "reIndex":    
        channel_ids = json.loads(request.POST.get("channel_ids", "[]"))
        index = 1
        for channel_id in channel_ids:
            try:
                channel = models.Channel.objects.get(id=channel_id, owner = request.user)
            except Exception as e:
                print(e)
            if channel.index != index:
                channel.index = index
                channel.save(update_fields=["index"])
            index += 1
            
        return JsonResponse({'status':'OK'})
        
        
    try:
        channel = models.Channel.objects.get(id=request.POST.get("channel_id", ""), owner = request.user)
    except:
        return JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})
                   
    if command == "addSource":
        try:
            path = json.loads(request.POST.get("path", "[]"))
        except:
            return JsonResponse({'status':"error","message": "Failed to load item path"})
            
        tmp = [x for x in path]
        while True:
            try:    
                s = json.dumps(tmp,separators=(',', ':'))
                models.ChannelSource.objects.get(path=s, channel = channel)  
                return JsonResponse({'status':'ERROR',"message":"Source already exists"})
            except Exception as e:
                pass
            if len(tmp) == 0:   
                break
            tmp = tmp[:-1]
        channelSource = models.ChannelSource()
        channelSource.channel = channel
        channelSource.path = json.dumps(path,separators=(',', ':'))
        channelSource.save()
        channel.upfill_errorcount = 0
        channel.save(update_fields=["upfill_errorcount"])
        return JsonResponse({'status':'OK'})      
        
    if command == "addVideo":
        try:
            sourcePath = json.loads(request.POST.get("path", "[]"))
        except:
            return JsonResponse({'status':"error","message": "Failed to load item path"})
        
        item, items = kodinoRoot.resolveHashPath(sourcePath)
        d = item.getDuration()
        if d > 10 and d < 36000: # 10h
            u = models.Upcoming()
            u.channel = channel
            u.addon = item.addon.id
            u.url = item.url
            u.title = item.title
            u.duration = d
            u.isFolder = item.isFolder
            path = item.getPath()
            u.path = json.dumps(path,separators=(',', ':'))
            u.thumbnailImage  = item.thumbnailImage
            u.save()
            stats.add("upcoming:videos_added", path)
            stats.add("upcoming:duration_added", path, u.duration)
            return JsonResponse({'status':'OK'})
        else:
            return JsonResponse({'status':"error", "message": "Sorry, this video can not be played"})
               
    if command == "addIncludeFilter":
        value = request.POST.get("value", "")
        
        channelIncludeFilter = models.ChannelIncludeFilter()
        channelIncludeFilter.channel = channel
        channelIncludeFilter.value = value
        channelIncludeFilter.save()
        channel.upfill_errorcount = 0
        channel.save(update_fields=["upfill_errorcount"])
        return JsonResponse({'status':'OK'})      
  
    if command == "addExcludeFilter":
        value = request.POST.get("value", "")
      
        channelIncludeFilter = models.ChannelExcludeFilter()
        channelIncludeFilter.channel = channel
        channelIncludeFilter.value = value
        channelIncludeFilter.save()
        channel.upfill_errorcount = 0
        channel.save(update_fields=["upfill_errorcount"])
        return JsonResponse({'status':'OK'})
        
    if command == "setAdultMode":
        adultmode = request.POST.get("adultmode", "")
        if adultmode not in ["all", "noadult", "adultonly"]:
            return  JsonResponse({'status':'ERROR', 'message' : "Unknown adult mode"})
        channel.adultmode = adultmode
        channel.save(update_fields=["adultmode"])
        return JsonResponse({'status':'OK'})           

    if command == "rename":
        newname = request.POST.get("newname", "")
        channel.name = newname
        channel.save(update_fields=["name"])
        return JsonResponse({'status':'OK'})           
    
    if command == "remove":
        channel.delete()
        for index in range(channel.index + 1 , 9999):
            try:
                channel = models.Channel.objects.get(index=index, owner = request.user)
                if channel.name == ("Channel %s" % channel.index):
                    channel.name = "Channel %s" % (channel.index -1)
                channel.index = index -1
                channel.save(update_fields=["name", "index"])
            except:
                break
        return JsonResponse({'status':'OK'})          

    return JsonResponse({'status':'ERROR',"message":"Unknown command '%s'" % command})
    
def _api_globalExcludeFilters(request):
    command = request.POST.get("command", "")
    if command == "get":
        try:
            globalExcludeFilters = models.GlobalExcludeFilter.objects.filter(owner = request.user)
        except:
            return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})
        return JsonResponse({'status':'OK', 'filters' : [f.toDict() for f in globalExcludeFilters ]})
        
    if command == "add":
        value = request.POST.get("value", "")
        if len(value) <= 0 or len(value) > 100:
            return JsonResponse({'status':'ERROR',"message":"A valid value must be set"})
            
        try:
            models.GlobalExcludeFilter.objects.get(value = value, owner = request.user)
            return JsonResponse({'status':'ERROR',"message":"Value already exists"})
        except:
            pass
        globalExcludeFilter = models.GlobalExcludeFilter()
        globalExcludeFilter.value = value
        globalExcludeFilter.owner = request.user
        globalExcludeFilter.save()
        return JsonResponse({'status':'OK'})
        
    if command == "remove":
        try:
            globalExcludeFilter =  models.GlobalExcludeFilter.objects.get(id=request.POST.get("filter_id", ""), owner = request.user)
        except:
            return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})

        globalExcludeFilter.delete()
        return JsonResponse({'status':'OK'})
   
    return JsonResponse({'status':'ERROR',"message":"Unknown command '%s'" % command})   
    
def _api_plugins(request):      
    global kodinoRoot 
  
    if request.user.is_superuser != True:
        return JsonResponse({'status':'ERROR',"message":"You must be superuser"})
        
    command = request.POST.get("command", "")
    if command == "list":
        plugins = [] 
        for i in kodinoRoot.plugins.getAvailablePlugins():
            try:
                description = i.getExtentionsByPoint("xbmc.addon.metadata")[0].description
            except Exception as e:
                description = ""
            try:
                summary = i.getExtentionsByPoint("xbmc.addon.metadata")[0].summary
            except Exception as e:  
                summary = ""
            try:
                broken = i.getExtentionsByPoint("xbmc.addon.metadata")[0].broken
            except Exception as e:  
                broken = False
            plugin = {  
                "id":i.id, 
                "name": i.name, 
                "version" : i.version, 
                "provider_name": i.provider_name,
                "isInstalled" : kodinoRoot.plugins.getInstalledById(i.id) != None,
                "summary" : summary,
                "description" : description,
                "source" : i.parent.id,
                "broken" : broken,
            }                       
            plugins.append(plugin)
        return JsonResponse({'status':'OK', 'plugins': plugins})   
        
    if command == "install":
        plugin_id = request.POST.get("plugin_id", "")
        kodinoRoot.plugins.install(plugin_id)
        kodinoRoot = kodino.Kodino()
        return JsonResponse({'status':'OK'})   
        
    if command == "uninstall":
        plugin_id = request.POST.get("plugin_id", "")
        kodinoRoot.plugins.uninstall(plugin_id)
        kodinoRoot = kodino.Kodino()
        return JsonResponse({'status':'OK'})    
        
    if command == "upgrade":
        kodinoRoot.plugins.update()
        kodinoRoot.plugins.upgrade()
        kodinoRoot = kodino.Kodino()
        return JsonResponse({'status':'OK'})           
 
    return JsonResponse({'status':'ERROR',"message":"Unknown command '%s'" % command})
    
def _api_stats(request):
    command = request.POST.get("command", "")
    if command == "playbackStarted":
        try:
            upcoming = models.Upcoming.objects.get(id=request.POST.get("upcoming_id", ""))
        except:
            return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})
        if upcoming.playback_started == False:
            upcoming.playback_started = True    
            upcoming.save()
            stats.add("playback:started", json.loads(upcoming.path))
        return JsonResponse({'status':'OK'})
        
    if command == "playbackDuration":
        try:
            upcoming = models.Upcoming.objects.get(id=request.POST.get("upcoming_id", ""))
        except:
            return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})
        value = int(request.POST.get("value", 0))
        if value > 0 and value < 200:
            stats.add("playback:duration_played", json.loads(upcoming.path), value)
        return JsonResponse({'status':'OK'})
     
    return JsonResponse({'status':'ERROR',"message":"Unknown command '%s'" % command})     
    
def _api_upcoming(request):
    command = request.POST.get("command", "")
    try:
        upcoming = models.Upcoming.objects.get(id=request.POST.get("upcoming_id", ""))
    except:
        return  JsonResponse({'status':'ERROR', 'message' : "Failed to receive object"})
        
    if(upcoming.channel.owner != request.user):
        return JsonResponse({'status': 'ERROR', "message": "You are not the owner of this video"})
    
    if command == "skipVideo": # manual skip
        upcoming.delete()
        stats.add("upcoming:videos_skipped", json.loads(upcoming.path))
        return JsonResponse({'status':'OK'})  
        
    if command == "skipVideoOnError": # video automatically skipped by player because of playback error
        upcoming.delete()
        stats.add("playback:error", json.loads(upcoming.path))
        return JsonResponse({'status':'OK'})
        
    if command == "endVideo": # video ended regulary
        upcoming.delete()
        stats.add("playback:ended", json.loads(upcoming.path))
        return JsonResponse({'status':'OK'})  
    
    return JsonResponse({'status':'ERROR',"message":"Unknown command '%s'" % command})
 



