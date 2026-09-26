<?php
require_once("init.php");

class GetAllDefs extends Request
{
    function __construct()
    {
        parent::__construct("ibs_defs.getAllDefs",array());
    }
}

class SaveDefs extends Request
{
    function __construct($defs)
    {
        parent::__construct("ibs_defs.saveDefs",array("defs"=>$defs));
    }

}

?>