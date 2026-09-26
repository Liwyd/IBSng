<?php
require_once("init.php");

class AddNewRas extends Request
{
    function __construct($ras_ip,$ras_description,$ras_type,$radius_secret,$comment)
    {
        parent::__construct("ras.addNewRas",array("ras_ip"=>$ras_ip,
                                              "ras_description"=>$ras_description,
                                              "ras_type"=>$ras_type,
                                              "radius_secret"=>$radius_secret,
                                              "comment"=>$comment));
    }
}

class GetRasInfo extends Request
{
    function __construct($ras_ip)
    {
        parent::__construct("ras.getRasInfo",array("ras_ip"=>$ras_ip));
    }
}

class GetActiveRasIPs extends Request
{
    function __construct()
    {
        parent::__construct("ras.getActiveRasIPs",array());
    }
}

class GetRasDescriptions extends Request
{
    function __construct()
    {
        parent::__construct("ras.getRasDescriptions",array());
    }
}

class GetInActiveRases extends Request
{
    function __construct()
    {
        parent::__construct("ras.getInActiveRases",array());
    }
}

class GetRasTypes extends Request
{
    function __construct()
    {
        parent::__construct("ras.getRasTypes",array());
    }
}

class GetRasAttributes extends Request
{
    function __construct($ras_ip)
    {
        parent::__construct("ras.getRasAttributes",array("ras_ip"=>$ras_ip));
    }
}

class GetRasPorts extends Request
{
    function __construct($ras_ip)
    {
        parent::__construct("ras.getRasPorts",array("ras_ip"=>$ras_ip));
    }
}

class UpdateRasInfo extends Request
{
    function __construct($ras_id,$ras_ip,$ras_description,$ras_type,$radius_secret,$comment)
    {
        parent::__construct("ras.updateRasInfo",array("ras_id"=>$ras_id,
                                              "ras_ip"=>$ras_ip,
                                              "ras_description"=>$ras_description,
                                              "ras_type"=>$ras_type,
                                              "radius_secret"=>$radius_secret,
                                              "comment"=>$comment));
    }
}



class UpdateRasAttributes extends Request
{
    function __construct($ras_ip,$attrs)
    {
        parent::__construct("ras.updateAttributes",array("ras_ip"=>$ras_ip,
                                              "attrs"=>$attrs));
    }
}

class ResetRasAttributes extends Request
{
    function __construct($ras_ip)
    {
        parent::__construct("ras.resetAttributes",array("ras_ip"=>$ras_ip));
    }
}

class AddRasPort extends Request
{
    function __construct($ras_ip,$port_name,$type,$phone,$comment)
    {
        parent::__construct("ras.addPort",array("ras_ip"=>$ras_ip,
                                                    "port_name"=>$port_name,
                                                    "phone"=>$phone,
                                                    "type"=>$type,
                                                    "comment"=>$comment
                                                    ));
    }
}

class GetPortTypes extends Request
{
    function __construct()
    {
        parent::__construct("ras.getPortTypes",array());
    }
}

class DelRasPort extends Request
{
    function __construct($ras_ip,$port_name)
    {
        parent::__construct("ras.delPort",array("ras_ip"=>$ras_ip,
                                                    "port_name"=>$port_name
                                                    ));
    }
}

class GetRasPortInfo extends Request
{
    function __construct($ras_ip,$port_name)
    {
        parent::__construct("ras.getRasPortInfo",array("ras_ip"=>$ras_ip,
                                                    "port_name"=>$port_name
                                                    ));
    }
}

class UpdateRasPort extends Request
{
    function __construct($ras_ip,$port_name,$type,$phone,$comment)
    {
        parent::__construct("ras.updatePort",array("ras_ip"=>$ras_ip,
                                                    "port_name"=>$port_name,
                                                    "phone"=>$phone,
                                                    "type"=>$type,
                                                    "comment"=>$comment
                                                    ));
    }
}


class DeActiveRas extends Request
{
    function __construct($ras_ip)
    {
        parent::__construct("ras.deActiveRas",array("ras_ip"=>$ras_ip));
    }
}

class ReActiveRas extends Request
{
    function __construct($ras_ip)
    {
        parent::__construct("ras.reActiveRas",array("ras_ip"=>$ras_ip));
    }
}

class GetRasIPpools extends Request
{
    function __construct($ras_ip)
    {
        parent::__construct("ras.getRasIPpools",array("ras_ip"=>$ras_ip));
    }
}

class AddIPpoolToRas extends Request
{
    function __construct($ras_ip,$ippool_name)
    {
        parent::__construct("ras.addIPpoolToRas",array("ras_ip"=>$ras_ip,
                                                   "ippool_name"=>$ippool_name
                                                   ));
    }
}

class DelIPpoolFromRas extends Request
{
    function __construct($ras_ip,$ippool_name)
    {
        parent::__construct("ras.delIPpoolFromRas",array("ras_ip"=>$ras_ip,
                                                     "ippool_name"=>$ippool_name
                                                     ));
    }
}

function getAllActiveRasInfos()
{
    /*
        return a list of associative dictionaries containing all active ras informations
    */
    $ras_infos=array();
    $ras_ips_request=new GetActiveRasIPs();
    list($success,$ras_ips)=$ras_ips_request->send();
    if(!$success)
        return array(FALSE,$ras_ips);
    $ras_info_request=new GetRasInfo("");
    foreach($ras_ips as $ras_ip)
    {
        $ras_info_request->changeParam("ras_ip",$ras_ip);
        list($success,$ras_info)=$ras_info_request->send();
        if(!$success)
            return array(FALSE,$ras_info);
        $ras_infos[]=$ras_info;
    }
    return array(TRUE,$ras_infos);
}

?>