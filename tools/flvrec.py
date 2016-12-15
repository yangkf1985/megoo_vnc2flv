#!/usr/bin/env python
##
##  flvrec.py - VNC to FLV recording tool.
##
##  Copyright (c) 2009-2010 by Yusuke Shinyama
##

import sys, time, socket, os, os.path, subprocess, signal
import threading #add by luoxiao
from vnc2flv.flv import FLVWriter
from vnc2flv.rfb import RFBNetworkClient, RFBError, PWDFile, PWDCache
from vnc2flv.video import FLVVideoSink, str2clip, str2size


##  flvrec
##
def flvrec(filename, host='localhost', port=5900,
           framerate=12, keyframe=120,
           preferred_encoding=(0,), pwdfile=None,
           blocksize=32, clipping=None,
           cmdline=None,
           debug=0, verbose=1):
    #add by luoxiao
    if debug:
        for e in preferred_encoding:
            print >>sys.stderr, 'flvrec - encoding: e=%d' % e
    #end add
    fp = file(filename, 'wb')
    if pwdfile:
        pwdcache = PWDFile(pwdfile)
    else:
        pwdcache = PWDCache('%s:%d' % (host,port))
    writer = FLVWriter(fp, framerate=framerate, debug=debug)
    sink = FLVVideoSink(writer,
                        blocksize=blocksize, framerate=framerate, keyframe=keyframe,
                        clipping=clipping, debug=debug)
    client = RFBNetworkClient(host, port, sink, timeout=500/framerate,
                              pwdcache=pwdcache, preferred_encoding=preferred_encoding,
                              debug=debug)
    if verbose:
        print >>sys.stderr, 'start recording'
    pid = 0
    if cmdline:
        pid = os.fork()
        if pid == 0:
            os.setpgrp()
            os.execvp('sh', ['sh', '-c', cmdline])
            sys.exit(1)
    retval = 0
    try: 
        #edit by luoxiao, 启动后台线程接受任意输入以结束进程
        #def sigint_handler(sig, frame):
        #    raise KeyboardInterrupt
        #signal.signal(signal.SIGINT, sigint_handler)
        stoped = [None]
        t = appSwitchThread(stoped)
        t.setDaemon(True) #设置为后台线程
        t.start()
        #end edit
        client.open()
        try:
            #edit by luoxiao
            #while 1:
            while stoped[0] == None:
                client.idle()
        finally:
            client.close()
    except KeyboardInterrupt:
        pass
    except socket.error, e:
        print >>sys.stderr, 'Socket error:', e
        retval = 1
    except RFBError, e:
        print >>sys.stderr, 'RFB error:', e
        retval = 1
    if pid:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    if verbose:
        print >>sys.stderr, 'stop recording'
    writer.close()
    fp.close()
    return retval

# 线程类读取任意的输入以结束程序
class appSwitchThread(threading.Thread):
    def __init__(self, stoped):  
        threading.Thread.__init__(self)
        self.stoped = stoped  
    def run(self):
        sys.stdin.readline() #读取控制台输入
        self.stoped[0] = object() #设置stoped不为None
    

# main
def main(argv):
    import getopt, vnc2flv
    def usage():
        print argv[0], vnc2flv.__version__
        print ('usage: %s [-d] [-q] [-o filename] [-r framerate] [-K keyframe]'
               ' [-e vnc_encoding] [-P vnc_pwdfile] [-N]'
               ' [-B blocksize] [-C clipping] [-S subprocess]'
               ' [host[:display] [port]]' % argv[0])
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'dqo:r:K:t:e:P:NB:C:S:')
    except getopt.GetoptError:
        return usage()
    debug = 0
    verbose = 1
    filename = 'out%s.flv' % time.strftime('%Y%m%d%H%M')
    framerate = 12
    keyframe = 120
    #edit by luoxiao ：添加"0xFFFFFF21"以支持服务器端分辨率调整的RfbEncoding消息（见vncview的RfbEncoding枚举）。
    #preferred_encoding = (0,)
    preferred_encoding = (0, 0xFFFFFF21)
    #end edit
    pwdfile = None
    cursor = True
    blocksize = 32
    clipping = None
    cmdline = None
    (host, port) = ('localhost', 5900)
    for (k, v) in opts:
        if k == '-d': debug += 1
        elif k == '-q': verbose -= 1
        elif k == '-o': filename = v
        elif k == '-r': framerate = int(v)
        elif k == '-K': keyframe = int(v)
        elif k == '-e': preferred_encoding = tuple( int(i) for i in v.split(',') )
        elif k == '-P': pwdfile = v
        elif k == '-N': cursor = False
        elif k == '-B': blocksize = int(v)
        elif k == '-C': clipping = str2clip(v)
        elif k == '-S': cmdline = v
    if not cursor:
        preferred_encoding += (-232,-239,)
    if 1 <= len(args):
        if ':' in args[0]:
            i = args[0].index(':')
            host = args[0][:i] or 'localhost'
            port = int(args[0][i+1:])+5900
        else:
            host = args[0]
    if 2 <= len(args):
        port = int(args[1])
    return flvrec(filename, host, port, framerate=framerate, keyframe=keyframe,
                  preferred_encoding=preferred_encoding, pwdfile=pwdfile,
                  blocksize=blocksize, clipping=clipping, cmdline=cmdline,
                  debug=debug, verbose=verbose)

if __name__ == "__main__": sys.exit(main(sys.argv))
