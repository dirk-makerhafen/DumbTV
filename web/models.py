from django.db import models
import random
from django.db.models import F, Q
import json
from django.contrib.auth import get_user_model
import time
from kodino import kodino
from kodino import kodinoPlugins
from kodino import kodinoItem


kodinoPlugin = None

# to be compatible with django > and < django2
try:
    User = get_user_model()
except:
    from django.contrib.auth.models import User

class GlobalExcludeFilter(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created', auto_now_add=True)
    updated  = models.DateTimeField('updated', auto_now=True)  
    value    = models.CharField( max_length=2000, default="")
    owner     = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def toDict(self):
        return {
            "id" : self.id,
            "created" : self.created,
            "updated" : self.updated,
            "value" : self.value,
        }   

class UserSetting(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created', auto_now_add=True)
    updated  = models.DateTimeField('updated', auto_now=True)  
    user     = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")
    
    allowAdult = models.BooleanField( default=False)
    
    def toDict(self):
        return {
            "id" : self.id,
            "created" : self.created,
            "updated" : self.updated,
        }   
    def __str__(self):
        return "Settings for %s" % ( self.user.username)
    
   
class Channel(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created', auto_now_add=True)
    updated  = models.DateTimeField('updated', auto_now=True)  
    owner     = models.ForeignKey(User, on_delete=models.CASCADE, related_name="channels")
    
    name     = models.CharField( max_length=2000, default="")
    
    description = models.CharField( max_length=10000, default="")
    index = models.IntegerField( default=0)
    
    upfill_lastrun = models.IntegerField( default=0)
    upfill_lastsuccess = models.IntegerField( default=0)
    upfill_lastfail = models.IntegerField( default=0)
    upfill_active = models.BooleanField( default=False)
    upfill_errorcount = models.IntegerField( default=0)
    
    adultmode     = models.CharField( max_length=200, default="noadult") # all, noadult, adultonly
    
    class Meta:
        ordering = ["index"]
     
    def toDict(self):
        c = self.get_current_video()
        if c != None:
            startposition, currentvideo = c
            currentvideo = currentvideo.toDict()
        else:
            startposition, currentvideo = 0,None
        return {
        
            "id" : self.id,
            "created" : self.created,
            "updated" : self.updated,
            "name" : self.name,
            "description" : self.description,
            "sources" : [s.toDict() for s in self.sources.all()],
            "upcoming" : [s.toDict() for s in self.upcoming.all()],
            "excludefilters" : [s.toDict() for s in self.excludefilters.all()],
            "includefilters" : [s.toDict() for s in self.includefilters.all()],
            "index" : self.index,
            "upfill_active" : self.upfill_active,
            "currentvideo_startposition" : startposition,
            "currentvideo" : currentvideo,
            "adultmode" : self.adultmode,
        }
        
    def __str__(self):
        return "Channel %s id:%s name:%s" % ( self.index, self.id, self.name)
 
    def get_current_video(self):
        #return tuplen of startposition and video
        MAX_SKIP = 2
        for nroftrial in range(0,10):
            for channel in self.owner.channels.all():
                try:
                    upcoming = channel.upcoming.all()[0]
                    if upcoming.starttime == 0:
                        upcoming.starttime = int(time.time())
                        upcoming.save()
                except:
                    pass
            try:
                currentvideo = self.upcoming.all()[0]
            except:
                return None

            offset = currentvideo.duration - (int(time.time()) - currentvideo.starttime )
            if offset < 0:
                print("offset < 0")
                if nroftrial < MAX_SKIP: 
                    print("trials reached")
                    try:
                        nextvideo = self.upcoming.all()[1] #
                        nextvideo.starttime = int(time.time()) + offset 
                        nextvideo.save()
                    except: 
                        print("# no more videos found, use last one" )
                        currentvideo.starttime = int(time.time())
                        currentvideo.save()
                        continue
                    print("# set next video starttime into future")
                currentvideo.delete()
                print("currentvideo.delete()")
                continue
            else:
                startposition = currentvideo.duration - offset
                break
        return startposition, currentvideo
   
   
class ChannelExcludeFilter(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created', auto_now_add=True)
    updated  = models.DateTimeField('updated', auto_now=True)  
    value    = models.CharField( max_length=2000, default="")
    channel  = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='excludefilters')

    def toDict(self):
        return {
            "id" : self.id,
            "created" : self.created,
            "updated" : self.updated,
            "value" : self.value,
        }   

        
class ChannelIncludeFilter(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created', auto_now_add=True)
    updated  = models.DateTimeField('updated', auto_now=True)  
    value    = models.CharField( max_length=2000, default="")
    channel  = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='includefilters')

    def toDict(self):
        return {
            "id" : self.id,
            "created" : self.created,
            "updated" : self.updated,
            "value" : self.value,
        }   

 
class ChannelSource(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created', auto_now_add=True)
    updated  = models.DateTimeField('updated', auto_now=True)
    channel  = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='sources')
    path = models.CharField( max_length=10000, default="")
    
    def toDict(self):
        return {        
            "id" : self.id,
            "created" : self.created,
            "updated" : self.updated,
            "path" : json.loads(self.path),
            "channelId" : self.channel.id,
        }
     
    
class Upcoming(models.Model):
    id       = models.AutoField(primary_key=True)
    created  = models.DateTimeField('created',auto_now_add=True)
    updated  = models.DateTimeField('updated',auto_now=True)  
    channel  = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='upcoming')
    
    addon = models.CharField( max_length=1000,default="")
    url = models.CharField( max_length=10000,default="")
    title = models.CharField( max_length=10000,default="")
    thumbnailImage = models.CharField( max_length=10000,default="")

    path = models.CharField( max_length=10000,default="")

    
    duration = models.IntegerField( default=0)
    starttime = models.IntegerField( default=0) 
    playback_started = models.BooleanField( default=False)
    
    def getPlaybackUrl(self):
        global kodinoPlugin
        if kodinoPlugin == None:
            kodinoPlugin = kodinoPlugins.KodinoPlugins()
        addon = kodinoPlugin.getInstalledById(self.addon)
        
        k = kodinoItem.KodinoItem( addon, self.url, self.title, "file", self.thumbnailImage, False, parent = None, username = self.channel.owner.username)
        return k.getPlaybackUrl()
        
        
    class Meta:
        ordering = ["created"]
    
    def toDict(self):
        return {        
            "id" : self.id,
            "created" : self.created,
            "updated" : self.updated,
            "addon" : self.addon,
            "url" : self.url,
            "title" : self.title,
            "thumbnailImage" : self.thumbnailImage,
            "path" : json.loads(self.path),
            "duration" : self.duration,
            "channelId" : self.channel.id,
            "starttime" : self.starttime,
        }    
        
        
        