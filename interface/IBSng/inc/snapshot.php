<?php
require_once("init.php");

class GetRealTimeSnapShot extends Request
{
    function __construct($name)
    {
        parent::__construct("snapshot.getRealTimeSnapShot",array("name"=>$name));
    }
}

class GetBWSnapShotForUser extends Request
{
    function __construct($user_id,$ras_ip,$unique_id_val)
    {
        parent::__construct("snapshot.getBWSnapShotForUser",array("user_id"=>$user_id,
                                                              "ras_ip"=>$ras_ip,
                                                              "unique_id_val"=>$unique_id_val));
    }
}

class GetOnlinesSnapShot extends Request
{
    function __construct($conds,$type)
    {
        parent::__construct("snapshot.getOnlinesSnapShot",array("conds"=>$conds,
                                                           "type"=>$type));
    }
}

class GetBWSnapShot extends Request
{
    function __construct($conds)
    {
        parent::__construct("snapshot.getBWSnapShot",array("conds"=>$conds));
    }
}

?>