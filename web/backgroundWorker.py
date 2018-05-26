import json
import os
import time
import threading
import subprocess
import redis
import traceback
try:
    import queue
except:
    import Queue as queue
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

from kodino import kodino

VIDEO_REUSE_TIMEOUT = 3600*12
CHANNEL_THREADS = 20
CRAWLER_THREADS_PER_CHANNEL = 2

redis_connection = redis.StrictRedis(host='localhost', port=6379, db=4)

from .stats import Stats

stats = Stats()

class TreeWalker():
    def __init__(self,channel):
        self.channel = channel
        self.run = True
        self.itemsToRequest = []
        self.resultItems = []
        self.maxResults = 10
        self.maxRequests = 10
        self.requestCount = 0
        self.activeRequest = 0
        self.activeRequestLock = threading.Lock()

        self.channelExcludeFilters = [g.value.lower() for g in self.channel.excludefilters.all()]
        self.channelIncludeFilters = [g.value.lower() for g in self.channel.includefilters.all()]
        self.globalExcludeFilters = [g.value.lower() for g in models.GlobalExcludeFilter.objects.filter(owner=self.channel.owner)]
        
        self.known_item_hashes = {}
        self.current_request_items = [] # list of items that are currently requested
        
    def findItems(self, rootItems, maxResults = 10, maxRequests = 10):
        self.loadItems(rootItems)
        self.maxResults = maxResults
        self.maxRequests = maxRequests

        self.threads = []
        for _ in range(0,CRAWLER_THREADS_PER_CHANNEL):
            t = threading.Thread(target=self._workThread)
            t.daemon = True
            t.start()
            self.threads.append(t)
            
        for t in self.threads:
            t.join()
            
        if len(self.resultItems) > maxResults:
            self.resultItems = random.sample(self.resultItems, maxResults)
        return self.resultItems
        
    def _workThread(self):
        while self.run == True: 
            if len( self.resultItems) >= self.maxResults:
                return
            if self.requestCount >= self.maxRequests:
                return
            if len(self.itemsToRequest) == 0:
                if self.activeRequest == 0:
                    print("Nothing to request and no more active request, exiting thread")
                    return
                print("Request queue item, but active requests, waiting")
                time.sleep(1)
                continue
                
            try:
                item = self.itemsToRequest.pop(random.randint(0,len(self.itemsToRequest )- 1  ) )
            except Exception as e:
                print("Failed to pop item from list: %s" % e)
                self.run=False
                continue
                
            if item.requireKeyboard == True or item.isFolder == False:
                continue
                
            with self.activeRequestLock:
                self.requestCount  += 1
                self.activeRequest += 1    
                self.current_request_items.append(item)
                
            subItems = item.getSubItems()
            
            self.loadItems(subItems)
            
            with self.activeRequestLock:
                self.current_request_items.remove(item)
                self.activeRequest -= 1 
    
    def loadItems(self, kodiItems):
        badcnt = 0
        random.shuffle(kodiItems)
        for subItem in kodiItems:
            exclude = False
            subItem_filterable_title = subItem.title.lower()
            for globalExcludeFilter in self.globalExcludeFilters:
                if globalExcludeFilter in subItem_filterable_title:
                    exclude = True
                    break
            if exclude == True:
                continue
            for channelExcludeFilter in self.channelExcludeFilters:
                if channelExcludeFilter in subItem_filterable_title:
                    exclude = True
                    break                    
            if exclude == True:
                continue
                                                            
            if len( self.resultItems) >= self.maxResults:
                break
                
            if subItem.isFolder == False:
                found = True
                if self.channelIncludeFilters != []:
                    found = False
                    for channelIncludeFilter in self.channelIncludeFilters:
                        if channelIncludeFilter in subItem_filterable_title:
                            found = True
                            break
                if found == False:
                    continue
                knownVideoKey = "knownVideo:%s:%s" % (subItem.hash, self.channel.owner.username)
                if redis_connection.get(knownVideoKey) != None:
                    print("video is known")
                    continue
                redis_connection.set(knownVideoKey,True)
                redis_connection.expire(knownVideoKey, VIDEO_REUSE_TIMEOUT)                        
                d = subItem.getDuration()
                if len( self.resultItems) >= self.maxResults:
                    break
                if d > 10 and d < 36000: # 10h
                    subItem.duration = d
                    u = models.Upcoming()
                    u.channel = self.channel
                    u.addon = subItem.addon.id
                    u.url = subItem.url
                    u.title = subItem.title
                    u.duration = subItem.duration
                    u.isFolder = subItem.isFolder
                    path = subItem.getPath()
                    u.path = json.dumps(path,separators=(',', ':'))
                    u.thumbnailImage  = subItem.thumbnailImage
                    try:
                        u.save()
                    except:
                        print("Walker could not save upcoming, channel may be gone")
                        return
                    stats.add("upcoming:videos_added", path)
                    stats.add("upcoming:duration_added", path, u.duration)
                    self.resultItems.append(subItem)
                else:
                    badcnt += 1
                if badcnt > 3:
                    print("Too many bad sources, giving up on kodiItems")
                    return

            if subItem.isFolder == True and subItem.requireKeyboard == False:
                if len( self.resultItems) < self.maxResults:
                    if subItem.hash not in self.known_item_hashes:
                        self.known_item_hashes[subItem.hash] = True
                        if self.channel.adultmode == "noadult" and subItem.isAdult == True:
                            continue
                        if self.channel.adultmode == "adultonly" and subItem.isAdult == False:
                            continue
                        self.itemsToRequest.append(subItem)
                        
            if subItem.isFolder == True and subItem.requireKeyboard == True and self.channelIncludeFilters != []: # if we hit a search, random enter one of the includefilters
                subItems = subItem.getSubItems(random.choice(self.channelIncludeFilters))
                self.loadItems(subItems)


   
    
class UpcomingLoader():
    def __init__(self):
        print("UpcomingLoader.__init__")
        self.channel_request_queue = queue.Queue(5)
        self.isActive = False
        self.workthread = None
        self.counterLock = threading.Lock()
        self.active_thread_count = 0
        self.active_treewalker = []
        self.kodinoRoot = None
        
    def toDict(self):
        items = []
        for tw in self.active_treewalker:
            for item in tw.current_request_items:
                items.append(item.toDict())
        return {
        
            "isActive" : self.isActive,
            "channel_threads" : self.active_thread_count,
            "crawler_threads" : len(items),
            "items" : items,
        }
        
    def start(self):
        if self.isActive == True:   
            print("UpcomingLoader is already active")
            return
        print("UpcomingLoader.start")
        if self.kodinoRoot ==None:
            self.kodinoRoot = kodino.Kodino()
            
        self.isActive = True
        channels = models.Channel.objects.filter(upfill_active=True)
        for channel in channels:
            channel.upfill_active = False
            try:
                channel.save(update_fields=["upfill_active"])
            except:
                pass
                
        self.workthread = threading.Thread(target=self._workthread)
        self.workthread.daemon = True
        self.workthread.start() 
        for i in range(0,CHANNEL_THREADS):
            t = threading.Thread(target=self._loadUpcomingThread)
            t.daemon = True
            t.start() 
            
    def stop(self):
        self.isActive = False
        if self.workthread != None:
            self.workthread.join()
            
    def _workthread(self):
        while self.isActive == True:
            channels = models.Channel.objects.filter(upfill_errorcount__gt = 30, upfill_lastfail__lt = (int(time.time()) - 1800))
            for channel in channels:
                channel.upfill_errorcount = 25
                
            channels = models.Channel.objects.annotate(
                num_upcoming = Count('upcoming', distinct = True), 
                num_sources  = Count('sources',  distinct = True)
            ).filter(upfill_active=False, num_sources__gt=0, num_upcoming__lt=4, upfill_errorcount__lt = 30)
            
            for channel in channels:
                channel.upfill_active = True
                try:
                    channel.save(update_fields=["upfill_active"])
                except:
                    pass
                self.channel_request_queue.put(channel)
                if self.isActive == False:
                    break
            time.sleep(15)
            
    def _loadUpcomingThread(self):
        while self.isActive == True:
            channel = self.channel_request_queue.get()
            with self.counterLock:
                self.active_thread_count += 1
            channel.upfill_lastrun = int(time.time())
            startpoints = []
            for source in channel.sources.all():
                item, items  = self.kodinoRoot.resolveHashPath(json.loads(source.path))
                startpoints.append(item)
                startpoints.extend(items)
            if len(startpoints) != 0:
                print("Starting to look for more content")
                tw = TreeWalker(channel)
                self.active_treewalker.append(tw)
                items = tw.findItems(startpoints, maxResults = 3, maxRequests = 100)
                self.active_treewalker.remove(tw)
                cnt = len(items)
                if cnt > 0:
                    channel.upfill_lastsuccess = int(time.time())
                    channel.upfill_errorcount = 0
                else:
                    channel.upfill_lastfail = int(time.time())
                    channel.upfill_errorcount += 1 
                print("%s items load" % cnt)                
            self.channel_request_queue.task_done()
            channel.upfill_active = False
            try:
                channel.save(update_fields=["upfill_active", "upfill_errorcount", "upfill_lastfail", "upfill_lastsuccess"])
            except:
                pass
            with self.counterLock:
                self.active_thread_count -= 1
            
            
