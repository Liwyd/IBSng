from core.ibs_exceptions import *
from core.server import handler
from core.lib.multi_strs import MultiStr
import sys
import os
import traceback
import importlib.util

class UtilHandler(handler.Handler):
    def __init__(self):
        handler.Handler.__init__(self,"util")
        self.registerHandlerMethod("multiStrGetAll")
        self.registerHandlerMethod("runDebugCode")


    def multiStrGetAll(self,request):
        request.checkArgs("str","left_pad")
        return [x for x in MultiStr(request["str"],request["left_pad"])]

    def runDebugCode(self,request):
        request.needAuthType(request.ADMIN)
        request.checkArgs("command")
        requester=request.getAuthNameObj()
        if not requester.isGod():
            return "Access Denied"

        if "no_output" in request:
            self.__execCode(request)
            return True
        else:
            return self.__grabOutput(request)


    def __grabOutput(self, request):
        import pty
        out=""
        (pid, fd) = pty.fork()
        if pid == 0:
            try:
                self.__execCode(request)
            except:
                (_type,value,tback)=sys.exc_info()
                print("".join(traceback.format_exception(_type, value, tback)))
            
            sys.stdout.flush()
            os._exit(0)
        else:
            out = b""

            while True:
                (exit_pid, exit_status) = os.waitpid(pid, os.WNOHANG)

                try:
                    out += os.read(fd, 1024*1024)
                except OSError:
                    logException(LOG_DEBUG,"Debug Code Read:")

                if exit_pid == pid:
                    break

            return out.decode("utf-8",errors="replace")



    def __execCode(self, request):
        if "read_from_file" in request:
            module_name = os.path.basename(request["command"])[:-3]
            directory = os.path.dirname(request["command"])
            pathname = os.path.join(directory,module_name+".py")
            spec = importlib.util.spec_from_file_location(module_name,pathname)
            if spec is None or spec.loader is None:
                raise ImportError("cannot load %s"%pathname)
            module_object = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module_object
            try:
                spec.loader.exec_module(module_object)
            except:
                sys.modules.pop(module_name,None)
                raise
        else:
            exec( request["command"] )

