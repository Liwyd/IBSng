<?php
require_once("init.php");

class PostMessageToUser extends Request
{
    function __construct($user_ids, $message)
    {
        parent::__construct("message.postMessageToUser",array("user_ids"=>$user_ids,
                                                          "message"=>$message));
    }
}

class PostMessageToAdmin extends Request
{
    function __construct($message)
    {
        parent::__construct("message.postMessageToAdmin",array("message"=>$message));
    }
}

class GetAdminMessages extends Request
{
    function __construct($conds, $from, $to, $sort_by, $desc)
    {
        parent::__construct("message.getAdminMessages",array("conds"=>$conds,
                                                         "from"=>$from,
                                                         "to"=>$to,
                                                         "sort_by"=>$sort_by,
                                                         "desc"=>$desc));
    }
}

class GetUserMessages extends Request
{
    function __construct($conds, $from, $to, $sort_by, $desc)
    {
        parent::__construct("message.getUserMessages",array("conds"=>$conds,
                                                         "from"=>$from,
                                                         "to"=>$to,
                                                         "sort_by"=>$sort_by,
                                                         "desc"=>$desc));
    }
}

class DeleteUserMessages extends Request
{
    function __construct($message_ids)
    {
        parent::__construct("message.deleteUserMessages",array("message_ids"=>$message_ids));
    }
}

class DeleteAdminMessages extends Request
{
    function __construct($message_ids, $table)
    {
        parent::__construct("message.deleteMessages",array("message_ids"=>$message_ids,
                                                            "table"=>$table
                                                            ));
    }
}

class GetUserLastMessageID extends Request
{
    function __construct()
    {
        parent::__construct("message.getLastMessageID",array());
    }
}

?>