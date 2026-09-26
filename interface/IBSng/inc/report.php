<?php
require_once("init.php");
require_once("report_lib.php");


class GetOnlineUsers extends Request
{
    function __construct($normal_sort_by, $normal_desc, $voip_sort_by, $voip_desc, $conds)
    {
        parent::__construct("report.getOnlineUsers",array("normal_sort_by"=>$normal_sort_by,
                                                      "normal_desc"=>$normal_desc,
                                                      "voip_sort_by"=>$voip_sort_by,
                                                      "voip_desc"=>$voip_desc,
                                                      "conds"=>$conds));
    }
}

class GetConnections extends Request
{
    function __construct($conds,$from,$to,$sort_by,$desc)
    {
        parent::__construct("report.getConnections",array("conds"=>$conds,
                                                      "from"=>$from,
                                                      "to"=>$to,
                                                      "sort_by"=>$sort_by,
                                                      "desc"=>$desc));
    }    
}

class GetDurations extends Request
{
    function __construct($conds)
    {
        parent::__construct("report.getDurations",array("conds"=>$conds));
    }    
}

class GetGroupUsages extends Request
{
    function __construct($conds)
    {
        parent::__construct("report.getGroupUsages",array("conds"=>$conds));
    }    
}

class GetRasUsages extends Request
{
    function __construct($conds)
    {
        parent::__construct("report.getRasUsages",array("conds"=>$conds));
    }    
}

class GetAdminUsages extends Request
{
    function __construct($conds)
    {
        parent::__construct("report.getAdminUsages",array("conds"=>$conds));
    }    
}

class GetVoIPDisconnectCausesCount extends Request
{
    function __construct($conds)
    {
        parent::__construct("report.getVoIPDisconnectCauses",array("conds"=>$conds));
    }    
}

class GetSuccessfulCounts extends Request
{
    function __construct($conds)
    {
        parent::__construct("report.getSuccessfulCounts",array("conds"=>$conds));
    }    
}

class GetCreditChanges extends Request
{
    function __construct($conds,$from,$to,$sort_by,$desc)
    {
        parent::__construct("report.getCreditChanges",array("conds"=>$conds,
                                                      "from"=>$from,
                                                      "to"=>$to,
                                                      "sort_by"=>$sort_by,
                                                      "desc"=>$desc));
    }    
}

class GetUserAuditLogs extends Request
{
    function __construct($conds,$from,$to,$sort_by,$desc)
    {
        parent::__construct("report.getUserAuditLogs",array("conds"=>$conds,
                                                      "from"=>$from,
                                                      "to"=>$to,
                                                      "sort_by"=>$sort_by,
                                                      "desc"=>$desc));
    }    
}

class GetAdminDepositChangeLogs extends Request
{
    function __construct($conds,$from,$to,$sort_by,$desc)
    {
        parent::__construct("report.getAdminDepositChangeLogs",array("conds"=>$conds,
                                                      "from"=>$from,
                                                      "to"=>$to,
                                                      "sort_by"=>$sort_by,
                                                      "desc"=>$desc));
    }    
}


class DeleteReports extends Request
{
    function __construct($table, $date, $date_unit)
    {
        parent::__construct("report.delReports",array("table"=>$table,
                                                  "date"=>$date,
                                                  "date_unit"=>$date_unit));
    }    
}

class AutoCleanReports extends Request
{
    function __construct($connection_log_clean, $connection_log_unit,
                              $credit_change_clean, $credit_change_unit,
                              $user_audit_log_clean, $user_audit_log_unit,
                              $snapshots_clean, $snapshots_unit,
                              $web_analyzer_clean, $web_analyzer_unit)
    {
        parent::__construct("report.autoCleanReports",array("connection_log_clean"=>$connection_log_clean,
                                                        "connection_log_unit"=>$connection_log_unit,
                                                        "credit_change_clean"=>$credit_change_clean,
                                                        "credit_change_unit"=>$credit_change_unit,
                                                        "user_audit_log_clean"=>$user_audit_log_clean,
                                                        "user_audit_log_unit"=>$user_audit_log_unit,
                                                        "snapshots_clean"=>$snapshots_clean,
                                                        "snapshots_unit"=>$snapshots_unit,
                                                        "web_analyzer_clean"=>$web_analyzer_clean,
                                                        "web_analyzer_unit"=>$web_analyzer_unit));
    }    
}

class GetReportAutoCleanDates extends Request
{
    function __construct()
    {
        parent::__construct("report.getAutoCleanDates",array());
    }    
}

class GetWebAnalyzerReport extends Request
{
    function __construct($conds,$from,$to,$sort_by,$desc)
    {
        parent::__construct("web_analyzer.getWebAnalyzerLogs",array("conds"=>$conds,
                                                                "from"=>$from,
                                                                "to"=>$to,
                                                                "sort_by"=>$sort_by,
                                                                "desc"=>$desc));
    }    
}

class GetTopVisitedReport extends Request
{
    function __construct($conds, $from,$to)
    {
        parent::__construct("web_analyzer.getTopVisited",array("conds"=>$conds,
                                                                "from"=>$from,
                                                                "to"=>$to
                                                                ));
    }  
}

class GetConsoleBuffer extends Request
{
    function __construct()
    {
        parent::__construct("log_console.getConsoleBuffer",array());
    }    
}

class GetInOutUsages extends Request
{
    function __construct($conds,$from,$to)
    {
        parent::__construct("report.getInOutUsages",array("conds"=>$conds,
                                                      "from"=>$from,
                                                      "to"=>$to));
    }    
}

class GetCreditUsages extends Request
{
    function __construct($conds,$from,$to)
    {
        parent::__construct("report.getCreditUsages",array("conds"=>$conds,
                                                      "from"=>$from,
                                                      "to"=>$to));
    }    
}

class GetDurationUsages extends Request
{
    function __construct($conds,$from,$to)
    {
        parent::__construct("report.getDurationUsages",array("conds"=>$conds,
                                                      "from"=>$from,
                                                      "to"=>$to));
    }    
}


?>