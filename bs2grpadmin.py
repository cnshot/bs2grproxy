# BS2 GAE Reverse Proxy
# Russell <yufeiwu@gmail.com>
# Please use wisely

from bs2grpfile import *
from bs2grpconfig import *
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.api import memcache
import datetime

def redirect(response, url):
    response.set_status(307)
    response.headers['Location'] = url

def user_check(response):
    user = users.get_current_user()

    if user and users.is_current_user_admin():
        return True
    else:
        redirect(response, users.create_login_url(BS2GRPAdmin.BASE_URL))

    return False

class BS2GRPAdmin(webapp.RequestHandler):
    BASE_URL = r'/_bs2admin/'
    def get(self):
        if not user_check(self.response):
            return

        config = BS2GRPConfig.get_config()
        f = [users.create_logout_url("/bs2grpabout/")]
        f.append(BS2GRPAdminAction.BASE_URL)
        f.append(config.target_host)

        st_stat = []
        st_stat.append(BS2GRPFile.all().filter('status_code >=', 100).filter('status_code <', 200).count())
        st_stat.append(BS2GRPFile.all().filter('status_code =', 200).count())
        st_stat.append(BS2GRPFile.all().filter('status_code >=', 300).filter('status_code <', 400).count())
        st_stat.append(BS2GRPFile.all().filter('status_code >=', 400).filter('status_code <', 500).count())
        st_stat.append(BS2GRPFile.all().filter('status_code >=', 500).count())
        st_stat.append(reduce(lambda x,y: x+y, st_stat, 0))

        f.extend(st_stat)
        f.append(BS2GRPAdminAction.BASE_URL)
        f.append(BS2GRPAdminAction.BASE_URL)
        f.append(BS2GRPAdminAction.BASE_URL)
        f = tuple(f)

        self.response.set_status(200)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(
"""
<html>
<head>
<style>
h1{color:#fefe5c;}
body {font-family: Arial, "Microsoft Yahei", simsun; background-color:#000;color:#ddd;font-size:16px;}
a, a:visited {font-size:12px;color:#fff;padding-left:15px;}
a:hover {color:red;text-decoration:none;}
</style>
</head>
<body>
<center>
<table>
<tr><td width='550px'>
<h1>BS2 GAE Reverse Proxy Admin</h1>
</td><td width='100px'><a href='%s'>Log out</a></td></tr>
</table>
<form action='%s' method='get'>
<table>
<tr><td>Target Host: <input type='text' name='th' value='%s' /></td><td><input type='submit' value='Update' /></td></tr>
</table>
</form>
<p>Cached files:
<table>
<tr><td width='200px'>1xx Status</td><td width='100px'>%d</td></tr>
<tr><td>2xx Status</td><td>%d</td></tr>
<tr><td>3xx Status</td><td>%d</td></tr>
<tr><td>4xx Status</td><td>%d</td></tr>
<tr><td>>=5xx Status</td><td>%d</td></tr>
<tr><td>Total</td><td>%d</td></tr>
</table>
</p>
<table>
<tr><td nowrap width='100px'><a href='%s?fr=1'>Force Check</a></td><td>Force check cache on next client request regardless of CACHE_CHECK configuration</td></tr>
<tr><td nowrap><a href='%s?clear=1'>Clear All</a></td><td>Clear all cached files</td></tr>
<tr><td colspan=2><hr></td></tr>
<tr><td nowrap><a href='%s?rc=1'>Refresh Config</a></td><td>Clear the entity in memcache to refresh the config</td></tr>
</table>
</center>
</body>
</html>
""" % f)


class BS2GRPAdminAction(webapp.RequestHandler):
    BASE_URL = r'/_bs2adminaction/'
    def get(self):
        if not user_check(self.response):
            return

        body = ""
        force_check = self.request.get('fr')
        force_clear = self.request.get('clear')
        refresh_config = self.request.get('rc')
        target_host = self.request.get('th')

        if force_check:
            md = datetime.datetime.min
            ret = BS2GRPFile.all().filter('last_check >', md).fetch(1000)
            count = 0
            while ret:
                for i in ret:
                    i.last_check = md
                    i.put()
                count += len(ret)
                ret = BS2GRPFile.all().filter('last_check >', md).fetch(1000)
            body += "%d files are processed." % count

        if force_clear:
            ret = BS2GRPFile.all().fetch(1000)
            count = 0
            while ret:
                for i in ret:
                    i.delete()
                count += len(ret)
                ret = BS2GRPFile.all().fetch(1000)
            body += "%d files are deleted." % count

        if target_host:
            config = BS2GRPConfig.get_config()
            config.target_host = target_host
            config.put()
            refresh_config = True
            body += "Target host is set to %s." % target_host

        if refresh_config:
            try:
                memcache.delete('www')
                body += "Config is refreshed."
            except Exception, e:
                body += "Config is not refreshed. Error happened: " + str(e)

        self.response.set_status(200)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(
"""
<html>
<head>
<style>
h1{color:#fefe5c;}
body {font-family: Arial, "Microsoft Yahei", simsun; background-color:#000;color:#ddd;font-size:16px;}
a, a:visited {font-size:12px;color:#fff;padding-left:15px;}
a:hover {color:red;text-decoration:none;}
</style>
</head>
<body>
<center>
<h1>BS2 GAE Reverse Proxy Admin</h1>
<p><b>Action Result:</b></p>
<p>%s</p>
<p><a href="%s"><< Back</a></p>
</body>
</html>
""" % (body, BS2GRPAdmin.BASE_URL))
