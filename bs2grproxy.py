# GAPP Reverse Proxy by BS2
# Please use wisely
# yufeiwu@gmail.com

import wsgiref.handlers, urlparse, StringIO, logging, base64, zlib, re, traceback, logging, sys
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api import urlfetch_errors
from bs2grpconfig import BS2GRPConfig
from bs2grpfile import *

version = '1.0'

class BS2GRProxy(webapp.RequestHandler):
    IgnoreHeaders= ['connection', 'keep-alive', 'proxy-authenticate',
               'proxy-authorization', 'te', 'trailers',
               'transfer-encoding', 'upgrade', 'content-length', 'host']
    MediaExp = re.compile('.*\.(jpg|jpeg|gif|png|avi|mov|mp3|rm|rmvb|qt)$', re.IGNORECASE)
    CssJsExp = re.compile('.*\.(css|js)$', re.IGNORECASE)

    def permanent_redirect(self, url):
        logging.info("Redirecting to: " + url)
        self.response.set_status(301)
        self.response.headers['Location'] = str(url)
        return

    def process(self, path = None):
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
            if config.cache_static and (self.MediaExp.search(path_qs) or self.CssJsExp.search(path_qs)):
                need_cache = True

                # If client is expecting a 304 response, remember it
                after_date = newHeaders.get('If-Modified-Since', None)

                # Filter cache
                if after_date:
                    after_date = string_to_datetime(after_date)
                cache = BS2GRPFile.get_file(path_qs)
                logging.info("Cache result:" + str(cache))

                # If cache exists, we can make the fetch more efficient by adding If-Modified-Since header
                if cache and cache.mdatetime:
                    newHeaders['If-Modified-Since'] = cache.get_mdate()

                # Do a fetch to update the cache or if the cache doesn't exist. Otherwise simply return the cache
                if cache:
                    need_fetch = cache.need_check(config.cache_check)

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
                if after_date and after_date == cache.mdatetime:
                    # Don't return cached content since client already has a cached copy
                    # So just return a 304 response
                    self.response.set_status(304)
                    return
                elif (not after_date) or (after_date < cache.mdatetime):
                    # Cached file is newer
                    # Return cache
                    logging.info('Cache hit:' + cache.path)
                    self.response.set_status(200)
                    cache.to_headers(self.response.headers)
                    cache.to_string_io(self.response.out)
                    return
            elif resp.status_code == 404 and cache:
                # Remove cache
                cache.delete()
                cache = None
            elif resp.status_code == 200 and need_cache:
                # Need to cache the content
                logging.info('Caching:' + path_qs)
                if cache:
                    # Refresh cache
                    cache.clear_content()
                else:
                    cache = BS2GRPFile(path=path_qs, last_check = datetime.datetime.now())

                cache.etag = resp.headers.get('ETag', None)
                cache.mdatetime = string_to_datetime(resp.headers.get('Last-Modified', None))
                cache.content_type = resp.headers.get('Content-Type', None)
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
            logging.error(traceback.format_tb(tb, 5))
            return

    def post(self, path = None):
        return self.process(path)

    def get(self, path = None):
        return self.process(path)

    def head(self, path = None):
        return self.process(path)

def main():
    application = webapp.WSGIApplication([(r'/(.*)', BS2GRProxy)])
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()
