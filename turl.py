import cherrypy
import fcntl,md5,os,random,time,urllib2
import cPickle as pickle

KEYBASE = "pickle"
XMIN = 0x00
XMAX = 0xFFFFFFFF
NDIR = 4
DX = int(1.*(XMAX-XMIN)/NDIR)
SALT = "NaCl"

class Key:
    "Abstract class for accessing stored key/url pairs"
    def get(self):
        "Returns the value associate with this key"
    def put(self,url):
        "Associates a url with this key"
    def new(self):
        "Creates a new random key"

class FileKey(Key):
    "Store key/values using files"
    def __init__(self,key=''):
        if not key:
            self.new()
        else:
            self.key = key
            self.fname = self._loc()
    def get(self):
        """
        Returns the value associated with this key. Locking is performed on the
        key file to ensure only one person can access it at a time (and therefor
        maintain isolation and consistancy).
        """
        fp = file(self.fname,'r')
        fcntl.flock(fp,fcntl.LOCK_EX)
        key_dict = pickle.load(fp) 
        os.remove(self.fname)
        return key_dict[self.key]
    def put(self,url):
        """
        Opens the key file and stores the value to be associated with this key.
        File locking is also performed here (see FileKey.get for more details).
        """
        fp = file(self.fname,'w')
        fcntl.flock(fp,fcntl.LOCK_EX)
        key_dict = {self.key:url,'created':time.time()}
        pickle.dump(key_dict,fp)
        fcntl.flock(fp,fcntl.LOCK_UN)
        fp.close()
    def new(self):
        """
        Generates a new random key, then finds out which sub-directory it will
        go in and checks for an existing key. If the key is a duplicate, it is
        regenerated until a unique one is made
        """
        self.key = self._rand()
        self.fname = self._loc()
        while os.path.exists(self.fname):
            self.key = self._rand()
            self.fname = self._loc()
    def _loc(self):
        return "%s/%s/%s" % (
            KEYBASE,
            int(self.key,16)/DX,
            md5.new(SALT+self.key).hexdigest() )
    def _rand(self):
        return "%08x"%random.randint(XMIN,XMAX)


