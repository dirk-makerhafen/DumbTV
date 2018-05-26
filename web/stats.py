import json,os,random,time,redis, threading
redis_connection = redis.StrictRedis(host='localhost', port=6379, db=4)

ENDPOINT_CACHE_TIME = 3600 * 24 * 14 
TOTAL_CACHE_TIME = 3600 * 24 * 7

available_stats = [
    "upcoming:videos_found",
    "upcoming:videos_added",
    "upcoming:videos_skipped",
    "upcoming:duration_added",
    "playback:started",
    "playback:error",
    "playback:ended",
    "playback:duration_played",
]


class Stats():
    def __init__(self):
        self.isActive = False
        self.lastupdate = 0
        
    def add(self,key, path , value = 1):
        pathkey  = "/".join(x[0] for x in path)
        rediskey = "stats:%s:%s" % (key, pathkey)
        redis_connection.incrby(rediskey, value )
        redis_connection.expire(rediskey, ENDPOINT_CACHE_TIME)
        
    def get(self, path):
        results = {}
        pathkey = "/".join(x[0] for x in path)
        for available_stat in available_stats:
            r = redis_connection.get("stats:sum:%s:%s" % (available_stat, pathkey))
            if r != None:
                results[available_stat] = int(r)
            else:
                results[available_stat] = 0

        if results["upcoming:videos_added"] > 0:
            results["playback:errorrate"] = round(1.0 / results["upcoming:videos_added"] * results["playback:error"],4)
        else:
            results["playback:errorrate"] = 0
            
        if results["upcoming:duration_added"] > 0:
            results["playback:duration_playedrate"] =  round(1.0 / results["upcoming:duration_added"] * results["playback:duration_played"],4)
        else:
            results["playback:duration_playedrate"] = 0
            
            
        return results       
       
    def start(self):
        if self.isActive == True:   
            print("Stats updater is already active")
            return
        print("Stats.start")
        self.isActive = True
        self.workthread = threading.Thread(target=self._workthread)
        self.workthread.daemon = True
        self.workthread.start() 
            
    def stop(self):
        self.isActive = False
        if self.workthread != None:
            self.workthread.join()
            
    def _workthread(self):
        while self.isActive == True:
            if self.lastupdate < int(time.time()) -  1800:
                self.create()
            time.sleep(15)
       
    def create(self):
        self.lastupdate = int(time.time())
        for available_stat in available_stats:  
            #print("Creating stats for '%s'" % available_stat)
            newdata = {}
            keys = []
            itemkey = "stats:%s:*" % available_stat   
            for key in redis_connection.scan_iter(match="%s" % itemkey):
                keys.append(key)
            #print("%s items to consider" % len(keys))
            values = self.bulk_get(keys)
            for index in range(0, len(keys)):
                key, value = keys[index].decode("utf-8"), values[index]
                if value != None:
                    path = key.split(":")[-1]
                    for pathpart in self.pathToParts(path):
                        newkey =  "stats:sum:%s:%s" % (available_stat, pathpart)
                        try:
                            newdata[newkey] += int(value)
                        except:
                            newdata[newkey] = int(value)
            for key in sorted(newdata.keys()):
                redis_connection.set(key, newdata[key])
                redis_connection.expire(key, TOTAL_CACHE_TIME)
        cnt = 0
        for key in redis_connection.scan_iter(match="cache:*"):
            cnt += 1
        redis_connection.set("stats:cached_items",cnt)
        redis_connection.expire("stats:cached_items", TOTAL_CACHE_TIME)        
                
    def bulk_delete(self, keys):
        pipe = redis_connection.pipeline()
        for key in keys:
            pipe.delete(key)
        pipe.execute()
        
    def bulk_get(self, keys):
        pipe = redis_connection.pipeline(transaction=False)
        for key in keys:
            pipe.get(key)
        values = pipe.execute()
        return values 
        
    def pathToParts(self, path):
        results = []
        pathparts = path.split("/")
        while len(pathparts) > 0:
            results.append("/".join(pathparts))
            pathparts = pathparts[:-1]
        return results    
        
        
if __name__ == "__main__":
    Stats().create()
    
    
    