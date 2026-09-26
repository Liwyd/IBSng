<?php

class MultiStrGetAll extends Request
{
    function __construct($str,$left_pad)
    {
        parent::__construct("util.multiStrGetAll",array("str"=>$str,
                                                    "left_pad"=>$left_pad));
    }
}

function getAllMultiStrs($str,$left_pad=True)
{
    $req=new MultiStrGelAll($str,$left_pad);
    list($success,$str_arr)=$req->send();
    if($success)
        return $str_arr;
    return FALSE;
}
    
function isMultiString($str)
{
    return preg_match("/,|{[nl]{0,1}[0-9]+-[0-9]+}/",$str);
}

function getFirstOfMultiStr($str)
{
    $str_arr=getAllMultiStrs($str);
    if($str_arr===FALSE)
        return FALSE;
    else
        return $str_arr[0];
}

?>