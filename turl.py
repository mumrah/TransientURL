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
        self._checkdirs()
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
        if not os.path.exists(self.fname):
            return None
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
    def _checkdirs(self):
        if not os.path.exists(KEYBASE):
            os.mkdir(KEYBASE)
        for i in range(NDIR):
            if not os.path.exists("%s/%s"%(KEYBASE,i)):
                os.mkdir("%s/%s"%(KEYBASE,i))


class TransientURL(object):
    def index(self):
        out = """
        <h3>Enter super-secret url</h3>
        <form method="POST" action="create">
        <input type="text" name="url" value="http://example.com"/>
        <button type="submit">submit</button>
        </form>
        """
        return out
    index.exposed = True
    def create(self,url=None):
        if not url:
            return "<pre>You did not specify a URL</pre>"
        key = FileKey()
        key.put(url)
        hostname = "%(server.socket_host)s:%(server.socket_port)s" % cherrypy.config
        out = """
        <h3>Here is your URL, it's only good for one use, so use it wisely!</h3>
        <a href="http://%(hostname)s/get/%(key)s">http://%(hostname)s/get/%(key)s</a>
        """ % {'hostname':hostname,'key':key.key}
        return out
    create.exposed = True
    def get(self,key=None):
        """
        Retrieves the contents of the transient URL. Headers are passed through,
        as well as the content.
        """
        key = FileKey(key)
        url = key.get()
        if not url:
            return "<pre>Not Found</pre>"
        fp = urllib2.urlopen(url)
        for k in fp.headers:
            cherrypy.response.headers[k] = fp.headers[k]
        cherrypy.response.headers['Pragma'] = "no-cache"
        cherrypy.response.headers['Cache-Control'] = "no-cache"
        data = fp.read()
        fp.close()
        return data
    get.exposed = True

if __name__ == "__main__":
    cherrypy.quickstart(TransientURL(),config='cherrypy.conf')

"""
David Arthur, 2009
mumrah@gmail.com
"""
