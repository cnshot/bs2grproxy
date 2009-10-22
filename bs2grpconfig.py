# GAPP Reverse Proxy by BS2
# Please use wisely
# yufeiwu@gmail.com

from google.appengine.ext import db

# You can set them later directly in Database
# HTML target url
TARGET_HOST = "www.google.com"
# Static target url
STATIC_HOST = "www.google.com"
# Redirect css/js files to static host
CSSJS_REDIRECT = False
# Redirect media files to static host
MEDIA_REDIRECT = True

class BS2GRPConfig(db.Model):
    target_host = db.StringProperty(required=True)
    static_host = db.StringProperty(required=False, default='')
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
                media_redirect=MEDIA_REDIRECT,
                cssjs_redirect=CSSJS_REDIRECT)
            config.put()
        else:
            config = ret
        return config
