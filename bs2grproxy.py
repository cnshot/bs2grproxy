# BS2 GAE Reverse Proxy
# Russell <yufeiwu@gmail.com>
# Please use wisely

import wsgiref.handlers, urlparse, StringIO, logging, base64, zlib, re, traceback, logging, sys
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api import urlfetch_errors
from bs2grpconfig import BS2GRPConfig
from bs2grpfile import *
from bs2grpadmin import *

version = '1.0'

class BS2GRProxy(webapp.RequestHandler):
    IgnoreHeaders= ['connection', 'keep-alive', 'proxy-authenticate',
               'proxy-authorization', 'te', 'trailers',
               'transfer-encoding', 'upgrade', 'content-length', 'host']
    MediaExp = re.compile('.*\.(jpg|jpeg|gif|png|avi|mov|mp3|rm|rmvb|qt|ico)$', re.IGNORECASE)
    CssJsExp = re.compile('.*\.(css|js)$', re.IGNORECASE)

    def permanent_redirect(self, url):
        logging.info("Redirecting to: " + url)
        self.response.set_status(301)
        self.response.headers['Location'] = str(url)
        return

    def process(self, allow_cache = True):
        try:
            config = BS2GRPConfig.get_config()
            """logging.info("Config loaded:")
            logging.info("Target: " + config.target_host)
            logging.info("Static: " + str(config.static_host))
            logging.info("Media Redirect: " + str(config.media_redirect))
            logging.info("CSS/JS Redirect: " + str(config.cssjs_redirect))"""

            path_qs = self.request.path_qs
            method = self.request.method
            new_path = config.target_host + path_qs

            # Check method
            if method != 'GET' and method != 'HEAD' and method != 'POST':
                raise Exception('Method not allowed.')
            if method == 'GET':
                method = urlfetch.GET
            elif method == 'HEAD':
                method = urlfetch.HEAD
            elif method == 'POST':
                method = urlfetch.POST

            # Check path
            scm = self.request.scheme
            if (scm.lower() != 'http' and scm.lower() != 'https'):
                raise Exception('Unsupported Scheme.')
            new_path = scm + '://' + new_path

            # Redirects
            if (config.media_redirect and self.MediaExp.search(path_qs)) or \
                (config.cssjs_redirect and self.CssJsExp.search(path_qs)):
                new_path = scm + '://' + config.static_host + path_qs
                self.permanent_redirect(new_path)
                return

            newHeaders = dict(self.request.headers)
            newHeaders['Connection'] = 'close'

            # Try cache
            cache = None
            after_date = None
            need_cache = False
            need_fetch = True
            resp = None

            # Cachable file
            if allow_cache and config.cache_static and (self.MediaExp.search(path_qs) or self.CssJsExp.search(path_qs)):
                need_cache = True

                # If client is expecting a 304 response, remember it
                after_date = newHeaders.get('If-Modified-Since', None)

                # Filter cache
                if after_date:
                    after_date = string_to_datetime(after_date)
                cache = BS2GRPFile.get_file(path_qs, after_date)
                if cache:
                    logging.info("Cache result:" + cache.get_mdate())

                # If cache exists, we can make the fetch more efficient by adding If-Modified-Since header
                if cache and cache.mdatetime:
                    newHeaders['If-Modified-Since'] = cache.get_mdate()

                # Do a fetch to update the cache or if the cache doesn't exist. Otherwise simply return the cache
                if cache:
                    need_fetch = cache.need_check(config.cache_check)
                    if need_fetch:
                        logging.info("Cache update:" + cache.path)

                if after_date and not cache:
                    logging.info("No Cache 304 expectation:" + path_qs)

            # Do a fetch if needed
            if need_fetch:
                logging.info("Requesting target: " + new_path)
                for _ in range(config.retry):
                    try:
                        resp = urlfetch.fetch(new_path, self.request.body, method, newHeaders, False, False)
                        break
                    except urlfetch_errors.ResponseTooLargeError:
                        raise Exception('Response too large.')
                    except Exception:
                        continue
                else:
                    raise Exception('Target URL is not reachable: ' + new_path)

            # Refresh last check time stamp
            if cache and need_fetch:
                cache.last_check = datetime.datetime.now()
                cache.put()

            # Process cache
            if (not need_fetch) or (resp.status_code == 304 and cache):
                if after_date and cache.mdatetime and after_date == cache.mdatetime:
                    # Don't return cached content since client already has a cached copy
                    # So just return a 304 response
                    logging.info('Cache hit and 304:' + cache.path)
                    self.response.set_status(304)
                    return
                elif (not after_date) or (not cache.mdatetime) or (after_date < cache.mdatetime):
                    # Cached file is newer
                    # Return cache
                    logging.info('Cache hit %d:' % cache.status_code + cache.path)
                    self.response.set_status(cache.status_code)
                    cache.to_headers(self.response.headers)
                    #logging.info("HEADERS:\n" + str(self.response.headers))
                    cache.to_string_io(self.response.out)
                    return
            elif need_cache and (not 300 <= resp.status_code < 400):
                # Cache response except 3xx
                logging.info('Caching %d:' % resp.status_code + path_qs)
                if cache:
                    # Refresh cache
                    cache.clear_content()
                    cache.clear_headers()
                else:
                    cache = BS2GRPFile(path=path_qs, last_check = datetime.datetime.now())

                cache.status_code = resp.status_code
                cache.from_headers(resp.headers)
                cache.from_string(resp.content)
                cache.refresh_content_length()
                cache.put()

            # Forward response if no cache is provided
            self.response.set_status(resp.status_code)
            textContent = True
            for header in resp.headers:
                if header.strip().lower() in self.IgnoreHeaders:
                    continue

                self.response.headers[header] = resp.headers[header]

            self.response.out.write(resp.content)

        except Exception, e:
            self.response.out.write('BS2Proxy Error: %s.' % str(e))
            t1, t2, tb = sys.exc_info()
            logging.error('Exception:' + str(e))
            logging.error(traceback.format_tb(tb, 5))
            return

    def post(self):
        return self.process(False)

    def get(self,):
        return self.process(True)

    def head(self, path = None):
        return self.process(True)

class BS2GRPAbout(webapp.RequestHandler):
    def get(self):
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
<BR>
<table>
<tr><td nowrap>
<h1>BS2 GAE Reverse Proxy</h1>
</td><td width='100px'>
<a href='/bs2grpadmin/'>Admin</a>
</td></tr>
</table>
<p>Author: Russell (yufeiwu at gmail.com)
<a href='http://code.google.com/p/bs2grproxy/'>Project Homepage</a>
<a href='http://hi.baidu.com/ledzep2/'>Blog</a></p>
</center>
</body>
</html>
""")



def main():
    application = webapp.WSGIApplication([
        (r'/bs2grpadminaction/', BS2GRPAdminAction),
        (r'/bs2grpadmin/', BS2GRPAdmin),
        (r'/bs2grpabout/', BS2GRPAbout),
        (r'/.*', BS2GRProxy),
    ])
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()
