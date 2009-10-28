# BS2 GAE Reverse Proxy
# Russell <yufeiwu@gmail.com>
# Please use wisely


from google.appengine.ext import db
from email import utils
from time import mktime
import datetime


def datetime_to_string(dt):
    if not dt: return None
    stamp = mktime(dt.timetuple())
    return utils.formatdate(stamp, usegmt=True)

def string_to_datetime(s):
    if not s: return None
    t = utils.parsedate(s)[:-2]
    return datetime.datetime(*t)

# This model can overcome the limit of 1MB of data store for a single file IN THEORY
class BS2GRPFile(db.Model):
    path = db.StringProperty(required=True)
    status_code = db.IntegerProperty(required=False, default=200)
    mdatetime = db.DateTimeProperty(required=False)
    last_check = db.DateTimeProperty(required=False)
    content_type = db.StringProperty(required=False, default='')
    content_length = db.IntegerProperty(required=False, default=0)
    units = db.ListProperty(db.Blob)
    headers = db.StringListProperty()

    INTERESTED_HEADERS = ['etag', 'location']

    UNIT_LIMIT = 1024 * 1024 # 1 MB per unit

    @staticmethod
    def get_file(path, after_date = None, before_date = None):
        if not after_date and not before_date:
            return BS2GRPFile.get_by_key_name(path)

        ret = BS2GRPFile.all()
        ret.filter('path =', path)
        if after_date:
            ret.filter('mdatetime >=', after_date)
        if before_date:
            ret.filter('mdatetime <', before_date)
        ret.order('-mdatetime')
        return ret.get()

    def need_check(self, option):
        # If the cache need to be updated according to the check scheme
        if not self.last_check:
            return True

        now = datetime.datetime.now()
        diff = now - self.last_check
        if option == 'EOD':
            # End of day scheme
            if diff.days > 1 or now.day != self.last_check.day:
                return True
        elif not option or option == '0':
            # Check every time
            return True
        else:
            # Check after x days
            option = int(option)
            if diff.days >= option:
                return True

        return False

    def to_string_io(self, io):
        for i in self.units:
            io.write(i)

    def from_string(self, content):
        r = 0
        l = len(content)
        while r < l:
            _s = min(BS2GRPFile.UNIT_LIMIT, l - r)
            self.units.append(db.Blob(content[r:_s]))
            r += _s

    def refresh_content_length(self):
        if not self.content_length:
            self.content_length = reduce(lambda x, y: x + len(y), self.units, 0)
        return self.content_length

    def clear_content(self):
        self.content_length = None
        self.units = []

    def clear_headers(self):
        self.mdatetime = None
        self.content_type = None
        self.content_length = None
        self.headers = []

    def from_string_io(self, io):
        r = io.read(BS2GRPFile.UNIT_LIMIT)
        while len(r) > 0:
            self.units.append(db.Blob(r))
            r = io.read(BS2GRPFile.UNIT_LIMIT)

    def to_headers(self, headers):
        if self.mdatetime: headers['Last-Modified'] = str(self.get_mdate())
        if self.content_type: headers['Content-Type'] = str(self.content_type)
        if self.content_length: headers['Content-Length'] = str(self.content_length)
        for i in self.headers:
            k, v = i.split(':', 1)
            headers[str(k)] = str(v)

    def from_headers(self, headers):
        self.mdatetime = string_to_datetime(headers.get('Last-Modified', None))
        self.content_type = headers.get('Content-Type', None)
        for k in headers.keys():
            if k.lower() in BS2GRPFile.INTERESTED_HEADERS:
                header = "%s:%s" % (k, headers[k])
                self.headers.append(header)

    def get_mdate(self):
        return datetime_to_string(self.mdatetime)

    def set_mdate(self, s):
        self.mdatetime = string_to_datetime(s)




