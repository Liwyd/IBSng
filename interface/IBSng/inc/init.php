<?php
require_once ("defs.php");
require_once (IBSINC."session.php");
require_once (IBSINC."errors.php");
require_once (IBSINC."error.php");
require_once (IBSINC."auth.php");
require_once (IBSINC."request.php");
require_once (IBSINC."smarty.php");
require_once (IBSINC."lib.php");
require_once (IBSINC."lang.php");

session_init();
auth_init();

// baseline response hardening; SAMEORIGIN keeps the admin UI's own
// iframes working while blocking cross-site framing
header("X-Content-Type-Options: nosniff");
header("X-Frame-Options: SAMEORIGIN");
header("Referrer-Policy: same-origin");

require_once (IBSINC."referrer.php");

?>