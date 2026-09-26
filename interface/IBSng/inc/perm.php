<?php
require_once("init.php");

class AdminHasPerm extends Request
{
    function __construct($perm_name,$admin_username)
    {
        parent::__construct("perm.hasPerm",array("perm_name"=>$perm_name,
                                             "admin_username"=>$admin_username));
    }
}

class AdminCanDo extends Request
{
    function __construct($perm_name,$admin_username,$params)
    {
        parent::__construct("perm.canDo",array("perm_name"=>$perm_name,
                                           "admin_username"=>$admin_username,
                                           "params"=>$params));
    }
}


class AdminPermValue extends Request
{
    function __construct($perm_name,$admin_username)
    {
        parent::__construct("perm.getAdminPermVal",array("perm_name"=>$perm_name,"admin_username"=>$admin_username));
    }
}


function hasPerm($perm_name,$admin_username=null)
{/* check if athenticated admin has permission $perm_name
    return TRUE or FALSE
    on error write a message to log file and return FALSE
 */
    if(is_null($admin_username))
        $admin_username=getAuthUsername();

    $has_perm_request=new AdminHasPerm($perm_name,$admin_username);
    list($success,$ret_val)=$has_perm_request->send();
    if(!$success)
    {
        toLog("hasPerm Error:".$ret_val->getErrorMsg());
        return FALSE;
    }   
    return $ret_val==1?TRUE:FALSE;
}

function canDo($perm_name,$admin_username=null)
{/*check if authenticated admin can do a job needed permission with $perm_name
    perm_name(string) name of permission
    admin_username(string) if not null check canDo for this username, else use current logged on username
    other parameters of this function will be passed to core canDo function as optional arguments of permission
 */
    if(is_null($admin_username))
        $admin_username=getAuthUsername();

    $arg_list=func_get_args();
    $params=array();
    for($i=2;$i<func_num_args();$i++)
        $params[]=$arg_list[$i];

    $can_do_request=new AdminCanDo($perm_name,$admin_username,$params);
    list($success,$ret_val)=$can_do_request->send();
    if(!$success)
    {
        toLog("canDo Error:".$ret_val->getErrorMsg());
        return FALSE;
    }   
    return ($ret_val==TRUE)?TRUE:FALSE;
}

function amIGod()
{
    return hasPerm("GOD");
}


class GetPermsOfAdmin extends Request
{
    function __construct($admin_username)
    {
        parent::__construct("perm.getPermsOfAdmin",array("admin_username"=>$admin_username));
    }
}

class GetAllPerms extends Request
{
    function __construct($category)
    {
        parent::__construct("perm.getAllPerms",array("category"=>$category));
    }
}

class ChangePermission extends Request
{
    function __construct($admin_username,$perm_name,$perm_value)
    {
        parent::__construct("perm.changePermission",array("admin_username"=>$admin_username,
                                                      "perm_name"=>$perm_name,
                                                      "perm_value"=>$perm_value));
    }

}

class DeletePermission extends Request
{
    function __construct($admin_username,$perm_name)
    {
        parent::__construct("perm.delPermission",array("admin_username"=>$admin_username,
                                                      "perm_name"=>$perm_name));
    }
}

class DeletePermissionValue extends Request
{
    function __construct($admin_username,$perm_name,$perm_value)
    {
        parent::__construct("perm.delPermissionValue",array("admin_username"=>$admin_username,
                                                      "perm_name"=>$perm_name,
                                                      "perm_value"=>$perm_value));
    }
}

class SavePermsOfAdminToTemplate extends Request
{
    function __construct($admin_username,$template_name)
    {
        parent::__construct("perm.savePermsOfAdminToTemplate",array("admin_username"=>$admin_username,
                                                                "perm_template_name"=>$template_name));
    }
}

class GetListOfPermTemplates extends Request
{
    function __construct()
    {
        parent::__construct("perm.getListOfPermTemplates",array());
    }
}

class GetPermsOfTemplate extends Request
{
    function __construct($template_name)
    {
        parent::__construct("perm.getPermsOfTemplate",array("perm_template_name"=>$template_name));
    }
}

class LoadPermTemplateToAdmin extends Request
{
    function __construct($admin_username,$template_name)
    {
        parent::__construct("perm.loadPermTemplateToAdmin",array("admin_username"=>$admin_username,
                                                             "perm_template_name"=>$template_name));
    }
}

class DeletePermTemplate extends Request
{
    function __construct($template_name)
    {
        parent::__construct("perm.deletePermTemplate",array("perm_template_name"=>$template_name));
    }
}

function getPermsByCategory($perms)
{
    $categorized_perms=array("USER"=>array(),
                             "ADMIN"=>array(),
                             "RAS"=>array(),
                             "CHARGE"=>array(),
                             "MISC"=>array(),
                             "GROUP"=>array()
                            );
    foreach($perms as $perm_arr)
        $categorized_perms[$perm_arr["category"]][]=$perm_arr;
    return $categorized_perms;
}

function permValueRestricted($perm_name,$admin_name)
{/* return True if value of "$perm_name" of "$admin_name" is restricted
    Also return True if an error has been occured 
*/
    if (amIGod())
        return False;
    $req=new AdminPermValue($perm_name,$admin_name);
    $resp=$req->sendAndRecv();
    if($resp->isSuccessful())
    {
        if($resp->getResult()=="Restricted")
            return True;
        else
            return False;
    }
    else
        return True;
}
?>