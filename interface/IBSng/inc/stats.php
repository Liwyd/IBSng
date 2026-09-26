<?php
require_once("init.php");

class GetStatistics extends Request
{
    function __construct()
    {
        parent::__construct("stat.getStatistics",array());
    }
}

?>