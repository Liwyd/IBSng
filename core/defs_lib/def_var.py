import pickle
from core.ibs_exceptions import *
from core.lib.general import *
import types


class DefVar:
    """
        Def Variable, instances of this class would be keep in memory (in a DefLoader instance)
    """
    def __init__(self,name,value):
        """
            value(string): pickled value of variable, we'll unpickle it
        """
        self.name=name
        self.__unpickleValue(value)

    def __unpickleValue(self,value):
        if isinstance(value, str):
            # python 3: DB drivers return text as str, pickle needs bytes
            value = value.encode("latin-1")
        # encoding="latin-1": values written by python 2 contain 8-bit
        # STRING opcodes; latin-1 preserves them (the default "ASCII" errors)
        self.value=pickle.loads(value, encoding="latin-1")
        self._type=type(self.value)

    def getValue(self):
        return self.value

    def getName(self):
        return self.name
    
    def getType(self):
        return self._type
    

class RawDefVar:
    """
        Raw Def Variable, used on add/updates
    """
    def __init__(self,var_name,var_value):
        """
            var_name(string): varibale name
            var_values(mixed): value of varible
        """
        self.name=var_name
        self.value=var_value

    def getName(self):
        return self.name
        
    def getValue(self):
        return self.value

    def castValue(self,_type):
        if _type==types.IntType or _type==types.BooleanType:
            self.value=to_int(self.value,self.name)
        elif _type==types.StringType:
            self.value=to_str(self.value,self.name)
        elif _type==types.ListType:
            if type(self.value)==types.DictType:
                self.value=self.value.values()
            self.value=to_list(self.value,self.name)
        else:
            raise GeneralException("%s has unsupported type %s"%(self.name,_type))
            
    def insertToDefsQuery(self):
        """
            
            return a query to insert variable "var_name" with value "var_value" to "defs" table
            value is pickled in order to keep variable type
            protocol 0 keeps the pickle ASCII text, so it fits the text column
            on every python version (python 3 defaults to a binary protocol)
        """
        from core.db import ibs_db
        return ibs_db.createInsertQuery("defs",{"name":dbText(self.name),
                                        "value":dbText(pickle.dumps(self.value,0))
                                        })

    def updateDefsQuery(self):
        """
            return an update query to change value(s) of "var_name" in "defs" table
        """
        from core.db import ibs_db
        return ibs_db.createUpdateQuery("defs",{"value":dbText(pickle.dumps(self.value,0))},
                                                "name=%s"%dbText(self.name))
