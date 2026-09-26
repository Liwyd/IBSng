from lib.error import *
import os
import sys
import importlib.util

class PluginLoader:
    def initPlugins(self,directory):
        """
            "directory"(text): directory path to search for plugins
            
            call init function of all *.py files in "directory"
            they must register themselves somewhere
            ex. user plugins should user plugins.registerUserPlugin
        """
        py_files=self.__getPyFiles(directory)
        module_obj_list=self.__loadModules(py_files,directory)
        self.__callInits(module_obj_list)
        

    def __callInits(self,mod_obj_list):
        """
            call init function of all modules in "mod_obj_list"
        """
        for obj in mod_obj_list:
            try:
                getattr(obj,"init")()
            except:
                logException("PluginLoader.__callInits %s"%obj)
    
    def __loadModules(self,file_list,directory):
        """
            load and import all files in "file_list" in path "directory"
            return a list of loaded objects
        """
        mod_obj_list=[]
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
                mod_obj_list.append(module_object)
            except:
                logException("PluginLoader.__loadModules")
        return mod_obj_list

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
            logException("PluginLoader.__getFilesList")
            return []
