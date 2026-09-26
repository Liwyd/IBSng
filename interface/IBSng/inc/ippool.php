<?php
require_once("init.php");

class AddNewIPpool extends Request
{
    function __construct($ippool_name,$comment)
    {
        parent::__construct("ippool.addNewIPpool",array("ippool_name"=>$ippool_name,
                                                    "comment"=>$comment));
    }
}

class UpdateIPpool extends Request
{
    function __construct($ippool_id,$ippool_name,$comment)
    {
        parent::__construct("ippool.updateIPpool",array("ippool_id"=>$ippool_id,
                                                    "ippool_name"=>$ippool_name,
                                                    "comment"=>$comment));
    }
}

class GetIPpoolNames extends Request
{
    function __construct()
    {
        parent::__construct("ippool.getIPpoolNames",array());
    }
}

class GetIPpoolInfo extends Request
{
    function __construct($ippool_name)
    {
        parent::__construct("ippool.getIPpoolInfo",array("ippool_name"=>$ippool_name));
    }
}

class DeleteIPpool extends Request
{
    function __construct($ippool_name)
    {
        parent::__construct("ippool.deleteIPpool",array("ippool_name"=>$ippool_name));
    }
}

class DelIPfromPool extends Request
{
    function __construct($ippool_name,$ip)
    {
        parent::__construct("ippool.delIPfromPool",array("ippool_name"=>$ippool_name,
                                                     "ip"=>$ip));
    }
}

class AddIPtoPool extends Request
{
    function __construct($ippool_name,$ip)
    {
        parent::__construct("ippool.addIPtoPool",array("ippool_name"=>$ippool_name,
                                                   "ip"=>$ip));
    }
}

function getIPpoolInfos()
{/*    
    Return an array of all ip pool infos in format (ippool_name=>associative_ippool_info_array)
 */
    $ippool_list_req=new GetIPpoolNames();
    list($success,$ippool_names)=$ippool_list_req->send();
    if(!$success)
        return array(FALSE,$ippool_names);
    else
    {
        $ippools_info=array();
        $ippool_info_req=new GetIPpoolInfo("");
        foreach($ippool_names as $ippool_name)
        {
            $ippool_info_req->changeParam("ippool_name",$ippool_name);
            list($success,$ippool_info)=$ippool_info_req->send();
            if(!$success)
                return array(FALSE,$ippool_info);
            else
                $ippools_info[$ippool_name]=$ippool_info;
        }
        return array(TRUE,$ippools_info);
    }
}


?>