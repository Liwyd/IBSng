from core.lib.general import *
from core.ibs_exceptions import logException, LOG_ERROR
import os
import sys
import importlib.util


def init():
    global plugin_loader
    plugin_loader=PluginLoader()
    
def loadPlugins(directory):
    """
        load plugins in "directory"
    """
    return plugin_loader.initPlugins(directory)

class PluginLoader:
    def initPlugins(self,directory):
        """
            directory(text): directory path to search for plugins
            
            return all loaded module object
            
            call init function of all *.py files in "directory"
            they must register themselves somewhere
            ex. user plugins should user plugins.registerUserPlugin
        """
        py_files=self.__getPyFiles(directory)
        modules=self.__loadModules(py_files,directory)
        self.__callInits(modules)
        return modules

    def __callInits(self, modules):
        """
            call init function of all modules in "modules" dic
        """
        for obj in modules.values():
            try:
                obj.init()
            except AttributeError: #no init defined
                pass
            except:
                logException(LOG_ERROR,"PluginLoader.__callInits")
    
    def __loadModules(self,file_list,directory):
        """
            load and import all files in "file_list" in path "directory"
            return a dic of loaded modules in format {module_name:module_obj}
        """
        modules={}
        for file_name in file_list:
            try:
                module_name=file_name[:-3] #remove trailing .py
                pathname=os.path.join(directory,file_name)
                spec=importlib.util.spec_from_file_location(module_name,pathname)
                if spec is None or spec.loader is None:
                    raise ImportError("cannot load %s"%pathname)
                module_object=importlib.util.module_from_spec(spec)
                sys.modules[module_name]=module_object
                try:
                    spec.loader.exec_module(module_object)
                except:
                    sys.modules.pop(module_name,None)
                    raise
                modules[module_name]=module_object
            except:
                logException(LOG_ERROR,"PluginLoader.__loadModules")
        return modules

    def __getPyFiles(self,directory):
        """
            return list of all .py files in directory
        """
        return [name for name in self.__getFilesList(directory) if name.endswith(".py")]

    def __getFilesList(self,directory):
        """
            return list of all files in "directory"
        """
        try:
            return os.listdir(directory)
        except OSError:
            logException(LOG_ERROR,"PluginLoader.__getFilesList")
            return []