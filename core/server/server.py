from core.server import handlers_manager,xmlrpcserver
from core.threadpool import thread_main
from core.stats import stat_main
from core import defs

def init():
    global server, server_started
    server_started = False
    handlers_manager.init()
    server=xmlrpcserver.XMLRPCServer((defs.IBS_SERVER_IP,defs.IBS_SERVER_PORT))
    
def startServer():

    stat_main.getStatKeeper().registerStat("server_avg_response_time", "seconds")    
    stat_main.getStatKeeper().registerStat("server_max_response_time", "seconds")
    stat_main.getStatKeeper().registerStat("server_total_requests", "int")

    global server_started
    server_started = True
    thread_main.runThread(server.serve_forever,[],"server")


def shutdown():
    if not server_started:
        return
    # no self-call needed (and none possible): requests are dropped while
    # shutting down, so a ServerProxy self-call would block forever.
    # serve_forever polls accept() every second (XMLRPCServer.timeout) and
    # exits as soon as main.isShuttingDown() is set.
    pass
