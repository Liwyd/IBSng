<?php

function session_init()
{
    if(!ini_get('session.auto_start'))
    {
        session_name("IBS_SESSID");
        // harden the session cookie: httpOnly (no script access), strict
        // id handling (reject uninitialized ids), SameSite to blunt CSRF
        ini_set('session.use_strict_mode', '1');
        ini_set('session.use_only_cookies', '1');
        ini_set('session.cookie_httponly', '1');
        if (PHP_VERSION_ID >= 70300)
            ini_set('session.cookie_samesite', 'Lax');
        $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
            || (isset($_SERVER['HTTP_X_FORWARDED_PROTO'])
                && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https');
        if ($https)
            ini_set('session.cookie_secure', '1');
        session_start();
    }
}

function sessionRegister($sess_var_name,$value)
{
    $_SESSION[$sess_var_name]=$value;
}


function sessionGetVar($var_name)
{
    return $_SESSION[$var_name];
}

function sessionIsSet($var_name)
{
    return isset($_SESSION[$var_name]);
}

?>