'''
factory.py

Copyright 2006 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import cgi
import json

from StringIO import StringIO

import core.controllers.outputManager as om
import core.data.kb.config as cf
import core.data.parsers.dpCache as dpCache
import core.data.parsers.wsdlParser as wsdlParser

from .HTTPPostDataRequest import HTTPPostDataRequest
from .HTTPQsRequest import HTTPQSRequest
from .JSONRequest import JSONPostDataRequest
from .WebServiceRequest import WebServiceRequest
from .XMLRPCRequest import XMLRPCRequest
from core.controllers.misc.encoding import smart_unicode
from core.controllers.w3afException import w3afException
from core.data.dc.cookie import Cookie
from core.data.dc.queryString import QueryString
from core.data.dc.header import Header
from core.data.parsers.urlParser import parse_qs
from core.data.url.HTTPRequest import HTTPRequest


__all__ = ['create_fuzzable_requests', 'create_fuzzable_request']

URL_HEADERS = ('location', 'uri', 'content-location')


def create_fuzzable_requests(resp, request=None, add_self=True):
    '''
    Generates the fuzzable requests based on an HTTP response instance.
    
    @parameter resp: An HTTPResponse instance.
    @parameter request: The HTTP request that generated the resp
    @parameter add_self: If I should add the current HTTP request
                         (@parameter request) to the result on not.
    
    @return: A list of fuzzable requests.
    '''
    res = []
    
    # Headers for all fuzzable requests created here:
    # And add the fuzzable headers to the dict
    headers = dict((h, '') for h in cf.cf.get('fuzzable_headers'))
    req_headers = dict(headers)
    req_headers.update(request and request.getHeaders() or {})
    
    # Get the cookie!
    cookieObj = _create_cookie(resp)
    
    # Create the fuzzable request that represents the request object
    # passed as parameter
    if add_self:
        qsr = HTTPQSRequest(
                    resp.getURI(),
                    headers=req_headers,
                    cookie=cookieObj
                    )
        res.append(qsr)
    
    headers = resp.getLowerCaseHeaders()
    
    # If response was a 30X (i.e. a redirect) then include the
    # corresponding fuzzable request.
    for url_header_name in URL_HEADERS:
        url_header_value = headers.get(url_header_name, '')
        if url_header_value:
            url = smart_unicode(url_header_value, encoding=resp.charset)
            try:
                absolute_location = resp.getURL().urlJoin(url)
            except ValueError:
                msg = 'The application sent a "%s" redirect that w3af' \
                      ' failed to correctly parse as an URL, the header' \
                      ' value was: "%s"'
                om.out.debug( msg % (url_header_name,url) )
            else:
                qsr = HTTPQSRequest(
                    absolute_location,
                    headers=req_headers,
                    cookie=cookieObj
                    )
                res.append(qsr)
    
    # Try to find forms in the document
    try:
        dp = dpCache.dpc.getDocumentParserFor(resp)
    except w3afException:
        # Failed to find a suitable parser for the document
        form_list = []
    else:
        form_list = dp.getForms()
        same_domain = lambda f: f.getAction().getDomain() == resp.getURL().getDomain()
        form_list = [f for f in form_list if same_domain(f)]
    
    if not form_list:
        # Check if its a wsdl file
        wsdlp = wsdlParser.wsdlParser()
        try:
            wsdlp.setWsdl(resp.getBody())
        except w3afException:
            pass
        else:
            for rem_meth in wsdlp.get_methods():
                wspdr = WebServiceRequest(
                                  rem_meth.getLocation(),
                                  rem_meth.getAction(),
                                  rem_meth.getParameters(),
                                  rem_meth.getNamespace(),
                                  rem_meth.get_methodName(),
                                  headers
                                  )
                res.append(wspdr)
    else:
        # Create one HTTPPostDataRequest for each form variant
        mode = cf.cf.get('fuzzFormComboValues')
        for form in form_list:
            for variant in form.getVariants(mode):
                if form.get_method().upper() == 'POST':
                    r = HTTPPostDataRequest(
                                        variant.getAction(),
                                        variant.get_method(),
                                        headers,
                                        cookieObj,
                                        variant,
                                        form.get_file_vars()
                                        )
                else:
                    # The default is a GET request
                    r = HTTPQSRequest(
                                  variant.getAction(),
                                  headers=headers,
                                  cookie=cookieObj
                                  )
                    r.setDc(variant)
                
                res.append(r)
    return res

XMLRPC_WORDS = ('<methodcall>', '<methodname>', '<params>',
                '</methodcall>', '</methodname>', '</params>')
def create_fuzzable_request(req_url, method='GET', post_data='',
                            add_headers=None):
    '''
    Creates a fuzzable request based on the input parameters.

    @param req_url: Either a url_object that represents the URL or a
        HTTPRequest instance. If the latter is the case the `method` and
        `post_data` values are taken from the HTTPRequest object as well
        as the values in `add_headers` will be merged with the request's
        headers.
    @param method: A string that represents the method ('GET', 'POST', etc)
    @param post_data: A string that represents the postdata.
    @param add_headers: A dict that holds the headers. If `req_url` is a
        request then this dict will be merged with the request's headers.
    '''
    if isinstance(req_url, HTTPRequest):
        url = req_url.url_object
        post_data = str(req_url.get_data() or '')
        method = req_url.get_method()
        headers = Header(req_url.headers)
        headers.update(add_headers or Header())
    else:
        url = req_url
        headers = add_headers or Header()

    # Just a query string request! No postdata
    if not post_data:
        return HTTPQSRequest(url, method, headers)
 
    else: # Seems to be something that has post data
        data = {}
        conttype = ''
        for hname in headers.keys():
            hnamelow = hname.lower()
            if hnamelow == 'content-length':
                del headers[hname]
            
            # TODO: What about repeated header names? Are we missing one for
            # loop here to address this structure? {'a': ['1', '2']}, please
            # note the awful [0] before the .lower().
            elif hnamelow == 'content-type':
                conttype = headers.get(hname, '')[0].lower()
        
        #
        # Case #1 - JSON request
        #
        try:
            data = json.loads(post_data)
        except:
            pass
        else:
            if data:
                return JSONPostDataRequest(url, method, headers, dc=data)
        
        #
        # Case #2 - XMLRPC request
        #
        if all(map(lambda stop: stop in post_data.lower(), XMLRPC_WORDS)):
            return XMLRPCRequest(post_data, url, method, headers)

        #
        # Case #3 - multipart form data - prepare data container
        #
        if conttype.startswith('multipart/form-data'):
            pdict = cgi.parse_header(conttype)[1]
            try:
                dc = cgi.parse_multipart(StringIO(post_data), pdict)
            except:
                om.out.debug('Multipart form data is invalid, the browser '
                             'sent something weird.')
            else:
                data = QueryString()
                data.update(dc)
                # We process multipart requests as x-www-form-urlencoded
                # TODO: We need native support of multipart requests!
                headers['content-type'] = ['application/x-www-form-urlencoded',]
                return HTTPPostDataRequest(url, method, headers, dc=data)
        
        #
        # Case #4 - a typical post request
        #
        try:
            data = parse_qs(post_data)
        except:
            om.out.debug('Failed to create a data container that '
                         'can store this data: "' + post_data + '".')
        else:
            # Finally create request
            return HTTPPostDataRequest(url, method, headers, dc=data)
            
        return None

def _create_cookie(http_response):
    '''
    Create a cookie object based on a HTTP response.

    >>> from core.data.parsers.urlParser import url_object
    >>> from core.data.url.httpResponse import httpResponse
    >>> url = url_object('http://www.w3af.com/')
    >>> headers = {'content-type': 'text/html', 'Cookie': 'abc=def' }
    >>> response = httpResponse(200, '' , headers, url, url)
    >>> cookie = _create_cookie(response)
    >>> cookie
    Cookie({'abc': ['def']})
    
    '''
    cookies = []
        
    # Get data from RESPONSE
    responseHeaders = http_response.getHeaders()
    
    for hname, hvalue in responseHeaders.items():
        if 'cookie' in hname.lower():
            cookies.append(hvalue)
                
    cookie_inst = Cookie(''.join(cookies))
    
    #
    # delete everything that the browsers usually keep to themselves, since
    # this cookie object is the one we're going to send to the wire
    #
    for key in ['path', 'expires', 'domain', 'max-age']:
        try:
            del cookie_inst[key]
        except:
            pass

    return cookie_inst 
