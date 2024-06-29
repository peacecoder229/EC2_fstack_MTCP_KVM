#!/usr/bin/python2.7
from __future__ import with_statement

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import os
import sys
import time
import pickle
import random
import hashlib
import argparse
import threading
import numpy as np

class WebPageParam( object ):
    """ Class to store the parameters to use when constructing a web page """
    
    def __init__( self, obj_dist="fixed", x=0.5, y=10.0 ):
        self.obj_dist = obj_dist
        self.x = x
        self.y = y
        self.obj_size = 1024000
        self.x_n = 0
        self.x_actual = 0.0
        self.y_actual = 0.0
        self.tot_demand = 0
        self.default_web_page_sizes = [
            1024,    # 1 KB
            8192,    # 8 KB
            10240,   # 10 KB
            32768,   # 32 KB
            65536,   # 64 KB
            102400,  # 100 KB
            262144,  # 256 KB
            524288,  # 512 KB
            786432,  # 768 KB
            1024000, # 1 MB
            4096000, # 4 MB
            2831155, # 2.7 MB
            10485760,# 10 MB

        ]        
        self.mu = 1431961.5 # Mid-point of default web page sizes
        self.index_mu = 5
        self.sigma = 1.0
        self.a = 2.0

class Handler( BaseHTTPRequestHandler ):
    """ Customized request handler to serve up variable sized web pages
    """

    def do_HEAD( self ):
        """ Respond to a HEAD request. """
        self.send_response( 200 )
        self.send_header( "Cache-Control", "max-age=31536000" )
        self.send_header( "Content-type", "text/plain" )
        self.end_headers( )

    def do_GET( self ):
        """ Respond to a GET request. """
        obj_size = self.select_obj_size( )
        web_page = self.create_web_page( obj_size )
        md5 = hashlib.md5( )
        md5.update( b"%s %s %s" % (self.command, self.path, self.request_version) )
        self.send_response( 200 )
        self.send_header( "Cache-Control", "max-age=31536000" )
        self.send_header( "Content-Length", "%d" % (len(web_page)) )
        self.send_header( "Content-type", "text/plain" )
        self.send_header( "Etag", "\"" + md5.hexdigest() + "\"" )
        # Note: Date is included by default in response header
        self.end_headers( )
        self.wfile.write( web_page )
        
        return

    def create_web_page( self, page_size ):
        """ Generate web page based on the URL, where page_size is the web page size in bytes.
        """
        sub_str = "%s %s %s" % ( self.command, self.path, self.request_version )
        content = sub_str * int( np.ceil((page_size / float(len(sub_str)))) )
        if len( content ) > page_size:
            content = content[:page_size]
        
        return content

    def log_message( self, format, *args):
        """ Suppress logging """
        return
    
    def select_obj_size( self ):
        web_page_param_file = os.path.join( os.path.dirname(os.path.realpath(__file__)), "web_page_param.pickle" )            
        with open( web_page_param_file, "rb" ) as input_file:
            web_page_param = pickle.load( input_file )            
        if ( web_page_param.obj_dist == "fixed" ):
            return 1024000
        else:
            if ( web_page_param.obj_dist == "gauss" ):
                index = int( round(np.random.normal(loc=web_page_param.index_mu, scale=web_page_param.sigma)) )
                index = max( 0, min(index, len(web_page_param.default_web_page_sizes) - 1) )
                return web_page_param.default_web_page_sizes[index]
            elif ( web_page_param.obj_dist == "zipf" ):
                index = np.random.zipf( web_page_param.a ) % len( web_page_param.default_web_page_sizes )
                return  web_page_param.default_web_page_sizes[index]
            elif ( web_page_param.obj_dist == "real" ):
                obj_size = random.choice( web_page_param.default_web_page_sizes )
                if web_page_param.x_actual < web_page_param.x:
                    obj_size = max( web_page_param.default_web_page_sizes )
                    y_perc_tot = float( web_page_param.tot_demand ) * ( web_page_param.y / 100.0 )
                    if ( y_perc_tot < float(max(web_page_param.default_web_page_sizes)) ):
                        obj_size = min( web_page_param.default_web_page_sizes, key=lambda a : abs(float(a) - y_perc_tot) )
                    if ( web_page_param.obj_size == obj_size ):
                        web_page_param.x_n += 1
                    else:
                        web_page_param.x_n = 1                       
                    web_page_param.obj_size = obj_size
                web_page_param.tot_demand += obj_size
                web_page_param.x_actual = float( web_page_param.x_n * web_page_param.obj_size ) / web_page_param.tot_demand
                with open( web_page_param_file, "wb" ) as output_file:
                    pickle.dump( web_page_param, output_file, protocol=pickle.HIGHEST_PROTOCOL )           
                return obj_size

class ThreadedHTTPServer( ThreadingMixIn, HTTPServer ):
    """ Handle each request in a separate thread. """
    
def port_type( x ):

    min_port = 8888
    max_port = 65535    

    x = int( x )
    if x < min_port:
        raise argparse.ArgumentTypeError( "Minimum port is %d" % (min_port) )
    elif x > max_port:
        raise argparse.ArgumentTypeError( "Maximum port is %d" % (max_port) )        
    
    return x
    
def main( argv ):

    script_dir = os.path.dirname( os.path.realpath(__file__) )
    web_page_param_file = os.path.join( script_dir, "web_page_param.pickle" )
        
    parser = argparse.ArgumentParser( description="Generates a web server that serves up objects according to the specified distribution." )
    parser.add_argument( "--host", dest="host_name", default="localhost",
                         help="Host name/IP address to use for the server" )
    parser.add_argument( "--port", dest="port_number", default=8888, type=port_type,
                         help="Port number to use for the server" )        
    parser.add_argument( "--obj-dist", dest="obj_dist", choices=["fixed", "gauss", "zipf", "real"], default="fixed",
                         help="Object Distribution Type" )
    parser.add_argument( "--perc-obj", dest="x", type=float, default=0.5,
                         help="Set percentage of objects for real distribution" )
    parser.add_argument( "--perc-tot", dest="y", type=float, default=10.0,
                         help="Set percentage of total demand for real distribution" )
    args = parser.parse_args()

    if ( args.obj_dist == "real" ):
        web_page_param = WebPageParam( obj_dist=args.obj_dist, x=args.x, y=args.y )
    else:
        web_page_param = WebPageParam( args.obj_dist )
        if ( args.obj_dist == "zipf" ):
            web_page_param.default_web_page_sizes.append( 0 ).reverse( )    

    with open( web_page_param_file, "wb" ) as output_file:
        pickle.dump( web_page_param, output_file, protocol=pickle.HIGHEST_PROTOCOL )

    server = ThreadedHTTPServer( (args.host_name, args.port_number), Handler )
    sys.stdout.write( "[%s]: Web Server Started - %s:%s\n" % (time.asctime(), args.host_name, args.port_number) )
    try:
        server.serve_forever( )
    except KeyboardInterrupt:
        server.server_close( )
    sys.stdout.write( "[%s]: Web Server Stopped - %s:%s\n" % (time.asctime(), args.host_name, args.port_number) )
    os.remove( web_page_param_file )

    return 0

if __name__ == '__main__':
    sys.exit( main(sys.argv) )
