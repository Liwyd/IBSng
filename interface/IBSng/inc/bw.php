<?php
require_once("init.php");

class AddInterface extends Request
{
    function __construct($interface_name,$comment)
    {
        parent::__construct("bw.addInterface",array("interface_name"=>$interface_name,
                                                    "comment"=>$comment));
    }
}

class AddNode extends Request
{
    function __construct($interface_name,$parent_id,$rate_kbits,$ceil_kbits)
    {
        parent::__construct("bw.addNode",array("interface_name"=>$interface_name,
                                           "parent_id"=>$parent_id,
                                           "rate_kbits"=>$rate_kbits,
                                           "ceil_kbits"=>$ceil_kbits));
    }
}

class AddLeaf extends Request
{
    function __construct($leaf_name,$parent_id,$default_rate_kbits,$default_ceil_kbits,$total_rate_kbits,$total_ceil_kbits)
    {
        parent::__construct("bw.addLeaf",array("leaf_name"=>$leaf_name,
                                           "parent_id"=>$parent_id,
                                           "default_rate_kbits"=>$default_rate_kbits,
                                           "default_ceil_kbits"=>$default_ceil_kbits,
                                           "total_rate_kbits"=>$total_rate_kbits,
                                           "total_ceil_kbits"=>$total_ceil_kbits));

    }
}

class AddLeafService extends Request
{
    function __construct($leaf_name,$protocol,$filter,$rate_kbits,$ceil_kbits)
    {
        parent::__construct("bw.addLeafService",array("leaf_name"=>$leaf_name,
                                                  "protocol"=>$protocol,
                                                  "filter"=>$filter,
                                                  "rate_kbits"=>$rate_kbits,
                                                  "ceil_kbits"=>$ceil_kbits
                                                  ));
    }
}

class GetInterfaces extends Request
{
    function __construct()
    {
        parent::__construct("bw.getInterfaces",array());
    }
}

class GetNodeInfo extends Request
{
    function __construct($node_id)
    {
        parent::__construct("bw.getNodeInfo",array("node_id"=>$node_id));
    }
}

class GetLeafInfo extends Request
{
    function __construct($leaf_name)
    {
        parent::__construct("bw.getLeafInfo",array("leaf_name"=>$leaf_name));
    }
}

class GetTree extends Request
{
    function __construct($interface_name)
    {
        parent::__construct("bw.getTree",array("interface_name"=>$interface_name));
    }
}

class DelLeafService extends Request
{
    function __construct($leaf_name,$leaf_service_id)
    {
        parent::__construct("bw.delLeafService",array("leaf_name"=>$leaf_name,
                                                  "leaf_service_id"=>$leaf_service_id));
    }
}

class GetAllLeafNames extends Request
{
    function __construct()
    {
        parent::__construct("bw.getAllLeafNames",array());
    }
}

class DelNode extends Request
{
    function __construct($node_id)
    {
        parent::__construct("bw.delNode",array("node_id"=>$node_id));
    }
}

class DelLeaf extends Request
{
    function __construct($leaf_name)
    {
        parent::__construct("bw.delLeaf",array("leaf_name"=>$leaf_name));
    }
}


class DelInterface extends Request
{
    function __construct($interface_name)
    {
        parent::__construct("bw.delInterface",array("interface_name"=>$interface_name));
    }
}

class UpdateInterface extends Request
{
    function __construct($interface_id,$interface_name,$comment)
    {
        parent::__construct("bw.updateInterface",array( "interface_id"=>$interface_id,
                                                    "interface_name"=>$interface_name,
                                                    "comment"=>$comment));
    }
}

class UpdateNode extends Request
{
    function __construct($node_id,$rate_kbits,$ceil_kbits)
    {
        parent::__construct("bw.updateNode",array("node_id"=>$node_id,
                                              "rate_kbits"=>$rate_kbits,
                                              "ceil_kbits"=>$ceil_kbits));
    }
}

class UpdateLeaf extends Request
{
    function __construct($leaf_id,$leaf_name,$default_rate_kbits,$default_ceil_kbits,$total_rate_kbits,$total_ceil_kbits)
    {
        parent::__construct("bw.updateLeaf",array("leaf_id"=>$leaf_id,
                                           "leaf_name"=>$leaf_name,
                                           "default_rate_kbits"=>$default_rate_kbits,
                                           "default_ceil_kbits"=>$default_ceil_kbits,
                                           "total_rate_kbits"=>$total_rate_kbits,
                                           "total_ceil_kbits"=>$total_ceil_kbits));

    }
}

class UpdateLeafService extends Request
{
    function __construct($leaf_name,$leaf_service_id,$protocol,$filter,$rate_kbits,$ceil_kbits)
    {
        parent::__construct("bw.updateLeafService",array("leaf_name"=>$leaf_name,
                                                  "leaf_service_id"=>$leaf_service_id,
                                                  "protocol"=>$protocol,
                                                  "filter"=>$filter,
                                                  "rate_kbits"=>$rate_kbits,
                                                  "ceil_kbits"=>$ceil_kbits
                                                  ));
    }
}

class AddBwStaticIP extends Request
{
    function __construct($ip_addr,$tx_leaf_name,$rx_leaf_name)
    {
        parent::__construct("bw.addBwStaticIP",array("ip_addr"=>$ip_addr,
                                              "tx_leaf_name"=>$tx_leaf_name,
                                              "rx_leaf_name"=>$rx_leaf_name));
    }
}

class UpdateBwStaticIP extends Request
{
    function __construct($static_ip_id,$ip_addr,$tx_leaf_name,$rx_leaf_name)
    {
        parent::__construct("bw.updateBwStaticIP",array("ip_addr"=>$ip_addr,
                                              "tx_leaf_name"=>$tx_leaf_name,
                                              "rx_leaf_name"=>$rx_leaf_name,
                                              "static_ip_id"=>$static_ip_id));
    }
}

class DelBwStaticIP extends Request
{
    function __construct($ip_addr)
    {
        parent::__construct("bw.delBwStaticIP",array("ip_addr"=>$ip_addr));
    }
}

class GetAllBwStaticIPs extends Request
{
    function __construct()
    {
        parent::__construct("bw.getAllBwStaticIPs",array());
    }
}

class GetBwStaticIPInfo extends Request
{
    function __construct($ip_addr)
    {
        parent::__construct("bw.getBwStaticIPInfo",array("ip_addr"=>$ip_addr));
    }
}

class GetAllActiveLeaves extends Request
{
    function __construct()
    {
        parent::__construct("bw.getActiveLeaves",array());
    }
}

class GetLeafCharges extends Request
{
    function __construct($leaf_name)
    {
        parent::__construct("bw.getLeafCharges",array("leaf_name"=>$leaf_name));
    }
}

?>