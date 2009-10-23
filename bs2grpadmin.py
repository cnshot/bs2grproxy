# BS2 GAE Reverse Proxy
# Russell <yufeiwu@gmail.com>
# Please use wisely

from bs2grpfile import *
from google.appengine.api import users
from google.appengine.ext import webapp
import datetime

def redirect(response, url):
    response.set_status(307)
    response.headers['Location'] = url

def user_check(response):
    user = users.get_current_user()

    if user and users.is_current_user_admin():
        return True
    else:
        redirect(response, users.create_login_url("/bs2grpadmin/"))

    return False

class BS2GRPAdmin(webapp.RequestHandler):
    def get(self):
        if not user_check(self.response):
            return

        f = [users.create_logout_url("/bs2grpabout/")]
        f.append(BS2GRPFile.all().filter('status_code >=', 100).filter('status_code <', 200).count())
        f.append(BS2GRPFile.all().filter('status_code =', 200).count())
        f.append(BS2GRPFile.all().filter('status_code >=', 300).filter('status_code <', 400).count())
        f.append(BS2GRPFile.all().filter('status_code >=', 400).filter('status_code <', 500).count())
        f.append(BS2GRPFile.all().filter('status_code >=', 500).count())
        f.append(reduce(lambda x,y: x+y, f[1:], 0))
        f = tuple(f)

        self.response.set_status(200)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(
"""
<html>
<head>
<style>
h1{color:#fefe5c;}
body {font-family: Arial, "Microsoft Yahei", simsun; background-color:0;color:#ddd;font-size:16px;}
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
<tr><td nowrap width='100px'><a href='/bs2grpadminaction/?fr=1'>Force Check</a></td><td>Force check cache on next client request regardless of CACHE_CHECK configuration</td></tr>
<tr><td nowrap><a href='/bs2grpadminaction/?clear=1'>Clear All</a></td><td>Clear all cached files</td></tr>
</table>
</center>
</body>
</html>
""" % f)


class BS2GRPAdminAction(webapp.RequestHandler):
    def get(self):
        if not user_check(self.response):
            return

        force_check = self.request.get('fr')
        force_clear = self.request.get('clear')

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
            body = "%d files are processed." % count

        if force_clear:
            ret = BS2GRPFile.all().fetch(1000)
            count = 0
            while ret:
                for i in ret:
                    i.delete()
                count += len(ret)
                ret = BS2GRPFile.all().fetch(1000)
            body = "%d files are deleted." % count

        self.response.set_status(200)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(
"""
<html>
<head>
<style>
h1{color:#fefe5c;}
body {font-family: Arial, "Microsoft Yahei", simsun; background-color:0;color:#ddd;font-size:16px;}
a, a:visited {font-size:12px;color:#fff;padding-left:15px;}
a:hover {color:red;text-decoration:none;}
</style>
</head>
<body>
<center>
<h1>BS2 GAE Reverse Proxy Admin</h1>
<p><b>Action Result:</b></p>
<p>%s</p>
<p><a href="/bs2grpadmin/"><< Back</a></p>
</body>
</html>
""" % body)
