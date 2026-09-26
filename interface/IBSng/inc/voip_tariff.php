<?php
require_once("init.php");

class AddNewTariff extends Request
{
    function __construct($tariff_name,$comment)
    {
        parent::__construct("voip_tariff.addNewTariff",array("tariff_name"=>$tariff_name,
                                                         "comment"=>$comment));
    }
}

class UpdateTariff extends Request
{
    function __construct($tariff_id,$tariff_name,$comment)
    {
        parent::__construct("voip_tariff.updateTariff",array("tariff_name"=>$tariff_name,
                                                         "tariff_id"=>$tariff_id,
                                                         "comment"=>$comment));
    }
}

class DeleteTariff extends Request
{
    function __construct($tariff_name)
    {
        parent::__construct("voip_tariff.deleteTariff",array("tariff_name"=>$tariff_name));
    }
}

class AddPrefix extends Request
{
    function __construct($tariff_name,$prefix_names,$prefix_codes,$cpms,$free_seconds,$min_durations,$round_tos,$min_chargable_durations)
    {
        parent::__construct("voip_tariff.addPrefix",array("tariff_name"=>$tariff_name,
                                                         "prefix_codes"=>$prefix_codes,
                                                         "prefix_names"=>$prefix_names,
                                                         "cpms"=>$cpms,
                                                         "free_seconds"=>$free_seconds,
                                                         "min_durations"=>$min_durations,
                                                         "round_tos"=>$round_tos,
                                                         "min_chargable_durations"=>$min_chargable_durations));
    }
}

class UpdatePrefix extends Request
{
    function __construct($tariff_name,$prefix_id,$prefix_name,$prefix_code,$cpm,$free_seconds,$min_duration,$round_to,$min_chargable_duration)
    {
        parent::__construct("voip_tariff.updatePrefix",array("tariff_name"=>$tariff_name,
                                                         "prefix_id"=>$prefix_id,
                                                         "prefix_code"=>$prefix_code,
                                                         "prefix_name"=>$prefix_name,
                                                         "cpm"=>$cpm,
                                                         "free_seconds"=>$free_seconds,
                                                         "min_duration"=>$min_duration,
                                                         "round_to"=>$round_to,
                                                         "min_chargable_duration"=>$min_chargable_duration));
    }
}

class DeletePrefix extends Request
{
    function __construct($tariff_name,$prefix_code)
    {
        parent::__construct("voip_tariff.deletePrefix",array("tariff_name"=>$tariff_name,
                                                         "prefix_code"=>$prefix_code));
    }
}

class GetTariffInfo extends Request
{
    function __construct($tariff_name,$include_prefixes=True,$name_regex="")
    {
        parent::__construct("voip_tariff.getTariffInfo",array("tariff_name"=>$tariff_name,
                                                         "include_prefixes"=>$include_prefixes,
                                                         "name_regex"=>$name_regex));
    }
}

class ListTariffs extends Request
{
    function __construct()
    {
        parent::__construct("voip_tariff.listTariffs",array());
    }
}


?>