<?php
require_once("init.php");

class AddNewGroup extends Request
{
    function __construct($name,$comment)
    {
        parent::__construct("group.addNewGroup",array("group_name"=>$name,
                                                 "comment"=>$comment,
                                                 ));
    }
}

class ListGroups extends Request
{
    function __construct()
    {
        parent::__construct("group.listGroups",array());
    }
}

class GetGroupInfo extends Request
{
    function __construct($group_name)
    {
        parent::__construct("group.getGroupInfo",array("group_name"=>$group_name));
    }
}

class UpdateGroup extends Request
{
    function __construct($group_id,$group_name,$comment,$owner_name)
    {
        parent::__construct("group.updateGroup",array("group_id"=>$group_id,
                                                  "group_name"=>$group_name,
                                                  "comment"=>$comment,
                                                  "owner_name"=>$owner_name));
    }
}

class UpdateGroupAttrs extends Request
{
    function __construct($group_name,$attrs,$to_del_attrs)
    {
        parent::__construct("group.updateGroupAttrs",array("group_name"=>$group_name,
                                                       "attrs"=>$attrs,
                                                       "to_del_attrs"=>$to_del_attrs));
    }
}

class DelGroup extends Request
{
    function __construct($group_name)
    {
        parent::__construct("group.delGroup",array("group_name"=>$group_name));
    }
}


function getAllGroupInfos()
{
    /*
        returns (TRUE,group_infos) or (FALSE,$err_obj)
        group_infos: a list of associative dictionaries containing all group informations
    */
    $group_infos=array();
    $group_names_request=new ListGroups();
    list($success,$group_names)=$group_names_request->send();
    if(!$success)
        return array(FALSE,$group_names);
    $group_info_request=new GetGroupInfo("");
    foreach($group_names as $group_name)
    {
        $group_info_request->changeParam("group_name",$group_name);
        list($success,$group_info)=$group_info_request->send();
        if(!$success)
            return array(FALSE,$group_info);
        $group_infos[]=$group_info;
    }
    return array(TRUE,$group_infos);
}

?>