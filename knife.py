#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
knife is a scalable mini-webframework based wsgi. It offers request routes with 
url parameter support and simple templates engines 

--------------------------The MIT License---------------------------
Copyright (c) 2011 Qi Wang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import os, sys, re, cgi, threading
from posixpath import normpath



def get_headers(env):
    return [(
        'Content-type',
        env.get('CONTENT_TYPE', "text/plain")
    )]



def get_req(env, **args):
    return updated(env, {
        'method'      : env.get('REQUEST_METHOD', "GET"),
        'path_info'   : env.get('PATH_INFO', ""),
        'http_host'   : env.get('HTTP_HOST', settings['http_host']),
        'args'        : args,
        'session' :  (env['com.saddi.service.session'].session 
                         if env.has_key('com.saddi.service.session') else None),
    })



def get_resp(content, status='200', content_type='text/plain'):
    return {
        'content' : content,
        'status' : settings['status_dic'][status],
        'content_type' : content_type
    }



def route(env):
    for k, v in settings['mapping']:
        sre = re.search(k, normpath(env['PATH_INFO']))
        if sre:
            args = sre.groupdict()
            for k_, v_ in args.items():
                args[k_] = v_[1:] if v_.startswith('/') else v_
                args[k_] = v_[:-1] if v_.endswith('/') else v_
            return k, v, args
    raise HTTP404Error


def get_app(env, start_response):

    local.tplstream = "" #reset tplstream 

    try:
        path, app_parts, args = route(env)
    except HTTP404Error:     
        start_response('404 error!', get_headers(env))
        return app_404()
    
    if env['REQUEST_METHOD'] == "POST":
        for k, v in cgi.parse_qs(env['wsgi.input'].read(
                int(env['CONTENT_LENGTH']))).items():
            args[k] = v if len(v) > 1 else v[0] 

    response = getattr(
        __import__(app_parts[0]), 
            app_parts[1])(get_req(env, **args)) if app_parts[0] else eval(
                app_parts[1])(get_req(env, **args))
        
    
    if response['status'] == settings['status_dic']["302"]:
        start_response("302 redirect!", [('Location', response['content'])])
        return []

    env['CONTENT_TYPE'] = response['content_type']
    start_response(response['status'], get_headers(env))
    return [response['content']]



def get_tpl(path, data={}):
    """ a simple template engine """

    path = "%s/%s" % (settings['template_dir'], path)
    startblocks = ('if', 'for')
    endblocks = ('endif', 'endfor')
    indent_width = 4
    stack = [
        "\n",
        '\n'.join(
            map(lambda x : "%s = %s" % (x[0], repr(x[1])),
                data.items()
            )
        )
    ]

    def getblock(line):
        return (re.split(r'[^a-zA-Z0-9_]', line)[0].rstrip(':')
            if line else ''
        )

    def translate(line):
        def linevar():
            for v in re.findall('{{.+?}}', line):
                yield v.replace("{{", "").replace("}}", "")
            yield ''

        return 'local.tplstream += ' + '+'.join(reduce(lambda x,y : x + y,
            zip(
                map(lambda x : repr(x),
                    re.split('{{.+?}}', line)
                ),
                linevar()
            )
        )).rstrip('+')
 
    def format(line):
        _indentfunc = lambda line, indent : stack.append(
            (''.join([' ' * indent, line])))
        prev_stack_indent = len(stack[-1]) - len(stack[-1].lstrip())
        indent = prev_stack_indent + \
            [0, indent_width][getblock(stack[-1]) in startblocks]

        if getblock(line) in startblocks:
            _indentfunc(line, indent)
        elif getblock(line) in endblocks:
            _indentfunc('', indent - indent_width)    
        else:
            _indentfunc(translate(line), indent)
            
    for line in open(path).read().splitlines(True):
        line = line.strip() if isinstance(line, unicode) \
               else unicode(line.strip(), encoding='utf8')
        format(line.replace("{% ","").replace(" %}",":"))

    eval(compile('\n'.join(stack), "<string>", "exec"))
    return local.tplstream.encode("utf-8")




"""
TEST SERVER
"""
def runserver():
    from wsgiref.simple_server import make_server        
    httpd = make_server(
        settings['host'], settings['port'], 
        get_app
    )
    print "Serving HTTP on port 8001..."
    httpd.serve_forever()



"""
TOOLS 
"""
def loop(var, funcs):
    for func in funcs:
        var = func(var)
    return var

def updated(dic,exdic):
    dic.update(exdic)
    return dic

def appended(li, item):
    li.append(item)
    return li

def extended(li, exli):
    li.extended(item)
    return li


"""
SETTINGS AND GLOBAL VAR
"""
try:
    from settings import config
except:
    config = {}

settings = {
    'http_host' : "http://127.0.0.1:8000",
    "host" : "127.0.0.1",
    "port" : 8001,
    'status_dic' : {
        "200" : "200 ok!",
        "302" : "302 redirect!",
        "404" : "404 app not find!"
    },
    'session' : lambda : lambda func : func,
    'middlewares' : [],
    'template_dir' : ".",
    'mapping' : [('^/$', ('','example_app'))],
}
settings.update(config)

get_headers = settings.get("get_headers", get_headers)
get_req = settings.get("get_req", get_req)
get_resp = settings.get("get_resp", get_resp)
route = settings.get("route", route)
get_app = loop(settings.get("get_app", get_app), settings['middlewares'])
get_tpl = settings.get("get_tpl", get_tpl)

runserver = settings.get("runserver", runserver)
redirect = lambda url : get_resp(url, status='302')
render = lambda p, d : get_resp(get_tpl(p, d), content_type="text/html")

app_404 = settings.get("app_404", lambda : ['404 error'])
HTTP404Error = type('HTTP404Error', (Exception,), {})
example_app = lambda req: get_resp("hello!")
local = threading.local()
local.tplstream = ""

def example_app(req):
    return get_resp("hello")


if __name__ == "__main__":
    runserver()
