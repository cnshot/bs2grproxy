# BS2 GAE Reverse Proxy
# Russell <yufeiwu@gmail.com>
# Please use wisely


from google.appengine.ext import db

# You can set them later directly in Database
# HTML target url
TARGET_HOST = "www.google.com"
# Static target url
STATIC_HOST = "www.google.com"
# Redirect css/js files to static host
CSSJS_REDIRECT = False
# Cache check option. value can be 'EOD' or 0 <= number.
# EOD: start checking after the end of the day (So 1 time per day)
# 0: Check every time
# x: Check every x day (After 24 * x hours)
CACHE_CHECK = 'EOD'
# Redirect media files to static host
MEDIA_REDIRECT = False
# Cache static files, Only work when REDIRECTs are disabled
CACHE_STATIC = True

class BS2GRPConfig(db.Model):
    target_host = db.StringProperty(required=True)
    static_host = db.StringProperty(required=False, default='')
    cache_static = db.BooleanProperty(required=True, default=False)
    cache_check = db.StringProperty(required=False)
    media_redirect = db.BooleanProperty(required=True, default=False)
    cssjs_redirect = db.BooleanProperty(required=True, default=False)
    retry = db.IntegerProperty(required=False, default=2)

    @staticmethod
    def get_config():
        ret = BS2GRPConfig.all().get()
        if not ret:
            config = BS2GRPConfig(
                target_host=TARGET_HOST,
                static_host=STATIC_HOST,
                cache_static=CACHE_STATIC,
                cache_check=CACHE_CHECK,
                media_redirect=MEDIA_REDIRECT,
                cssjs_redirect=CSSJS_REDIRECT)
            config.put()
        else:
            config = ret
        return config
