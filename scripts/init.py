#!/usr/bin/env python3
import sys
import importlib

sys.path.append("/usr/local/IBSng")
import curses
import os
import stat
import re
from core.lib import password_lib

apache_conf_dir = "/etc/httpd/conf.d"
apache_username = "apache"
logrotate_conf_dir = "/etc/logrotate.d"
pg_hba_conf = "/var/lib/pgsql/data/pg_hba.conf"
httpd_conf = "/etc/httpd/conf/httpd.conf"
selinux_config_file = "/etc/selinux/config"


def getDBConnection():
    from core import db_conf

    importlib.reload(db_conf)
    import pg

    con = pg.connect(
        dbname="IBSng",
        host=db_conf.DB_HOST,
        port=db_conf.DB_PORT,
        user=db_conf.DB_USERNAME,
        passwd=db_conf.DB_PASSWORD,
    )
    return con


def doSqlFile(con, file_name):
    content = open(file_name).read(1024 * 100)
    con.query(content)


def callAndGetLines(command):
    fd = os.popen("%s 2>&1" % command, "r")
    lines = fd.readlines()
    fd.close()
    return lines


def replaceInFile(filename, search_exp, replace_exp):
    try:
        with open(filename, "r") as file:
            content = file.read()
        new_content = re.sub(search_exp, replace_exp, content)
        with open(filename, "w") as file:
            file.write(new_content)
    except IOError:
        sys.exit("ERROR: Couldn't open or modify {}".format(filename))


def addToFile(filename, content, position="first"):
    try:
        with open(filename, "r+") as f:
            lines = f.readlines()
            if position == "first":
                lines.insert(0, content + "\n")
            elif position == "last":
                lines.append(content + "\n")
            else:
                raise ValueError("Invalid position. Use 'first' or 'last'.")
            f.seek(0)
            f.writelines(lines)
    except IOError:
        sys.exit("ERROR: Couldn't open or modify {}".format(filename))


def isContentInFile(filename, content):
    try:
        with open(filename, "r") as file:
            return content in file.read()
    except IOError:
        return False


# checking root
if os.getuid() != 0:
    sys.exit("ERROR: Install should be runned as root")

# checking pg module
try:
    import pg
except ImportError:
    sys.exit(
        "ERROR: Install should be runned as root\n \
              1-Install postgresql-python rpm on distribution CDs(redhat/fedora on last CD)\n \
              2-Download and install it from http://www.pygresql.org/"
    )

# trust ibsng pg pg_hba.conf
pg_hba_content = "local  IBSng   ibs            trust"
if not isContentInFile(pg_hba_conf, pg_hba_content):
    addToFile(pg_hba_conf, pg_hba_content)
    ret = os.system("systemctl restart postgresql")
    if ret != 0:
        sys.exit("ERROR: Failed to run 'systemctl restart postgresql'")

# checking db connection
try:
    con = getDBConnection()
    con.close()
except:
    exctype, exc_value = sys.exc_info()[:2]
    exc_value = str(exc_value)
    sys.exit("checking db connection Error occurred: " + exc_value)

# compile defs
ret = os.system("chmod 777 /usr/local/IBSng/core/defs_lib/defs2sql.py")
if ret != 0:
    sys.exit("ERROR: cant run chmod 777 /usr/local/IBSng/core/defs_lib/defs2sql.py")

ret = os.system(
    "/usr/local/IBSng/core/defs_lib/defs2sql.py -i /usr/local/IBSng/core/defs_lib/defs_defaults.py /usr/local/IBSng/db/defs.sql 1>/dev/null 2>/dev/null"
)
if ret != 0:
    sys.exit(
        "ERROR: File didn't compile successfully\nRecheck config file and try again"
    )

# insert table
con = None
try:
    con = getDBConnection()
    doSqlFile(con, "/usr/local/IBSng/db/tables.sql")
    doSqlFile(con, "/usr/local/IBSng/db/functions.sql")
    doSqlFile(con, "/usr/local/IBSng/db/initial.sql")
    doSqlFile(con, "/usr/local/IBSng/db/defs.sql")
    con.close()
except:
    if con:
        con.close()
    exctype, exc_value = sys.exc_info()[:2]
    exc_value = str(exc_value)
    sys.exit("insert table Error occured: " + exc_value)

# change system password
password = "system"
passwd_obj = password_lib.Password(password)
try:
    con = getDBConnection()
    con.query(
        "update admins set password='%s' where username='system'"
        % passwd_obj.getMd5Crypt()
    )
    con.close()
except:
    if con:
        con.close()
    exctype, exc_value = sys.exc_info()[:2]
    exc_value = str(exc_value)
    sys.exit("change system password Error occured: " + exc_value)

# create log dir
if not os.path.exists("/var/log/IBSng"):
    lines = callAndGetLines("mkdir /var/log/IBSng")
    if lines:
        sys.exit("ERROR: Couldn't make log dir." + " ".join(lines).strip())
lines = callAndGetLines("chmod 770 /var/log/IBSng")
if lines:
    sys.exit("ERROR: Couldn't chown log dir." + " ".join(lines).strip())

# setup httpd
if not os.path.exists(os.path.join(apache_conf_dir, "ibs.conf")):
    lines = callAndGetLines(
        "cp -f /usr/local/IBSng/addons/apache/ibs.conf %s" % apache_conf_dir
    )
    if lines:
        sys.exit(
            "ERROR: Couldn't copy ibs.conf to "
            + apache_conf_dir
            + " ".join(lines).strip()
        )
lines = callAndGetLines("chown root:%s /var/log/IBSng" % apache_username)
if lines:
    sys.exit(
        "ERROR: Couldn't change owner of /var/log/IBSng to "
        + apache_username
        + " ".join(lines).strip()
    )
lines = callAndGetLines(
    "chown %s /usr/local/IBSng/interface/smarty/templates_c" % apache_username
)
if lines:
    sys.exit(
        "ERROR: Couldn't change owner of /usr/local/IBSng/interface/smarty/templates_c to "
        + apache_username
        + " ".join(lines).strip()
    )

# copy log rotate
if not os.path.exists(os.path.join(logrotate_conf_dir, "IBSng")):
    lines = callAndGetLines(
        "cp -f /usr/local/IBSng/addons/logrotate/IBSng %s" % logrotate_conf_dir
    )
    if lines:
        sys.exit(
            "ERROR: Couldn't copy IBSng logrotate conf to "
            + logrotate_conf_dir
            + " ".join(lines).strip()
        )

# create ibsng service
if not os.path.exists("/etc/init.d/IBSng"):
    lines = callAndGetLines(
        "cp -f /usr/local/IBSng/init.d/IBSng.init.redhat /etc/init.d/IBSng"
    )
    if lines:
        sys.exit("ERROR: Couldn't copy init file." + " ".join(lines).strip())
ret = os.system("chmod 777 /etc/init.d/IBSng")
if ret != 0:
    sys.exit("ERROR: cant run chmod 777 /etc/init.d/IBSng")


# setup ibsng httpd.conf
httpd_conf_content = """ServerName 127.0.0.1
<Directory "/usr/local/IBSng/interface/IBSng">
    AllowOverride None
    Options None
    Require all granted
</Directory>"""
if not isContentInFile(httpd_conf, httpd_conf_content):
    addToFile(httpd_conf, httpd_conf_content)


# enable services
services = ["postgresql", "httpd", "IBSng"]
for service in services:
    ret = os.system("systemctl enable {}".format(service))
    if ret != 0:
        sys.exit("ERROR: Failed to enable {}".format(service))
for service in services:
    ret = os.system("systemctl restart {}".format(service))
    if ret != 0:
        sys.exit("ERROR: Failed to restart {}".format(service))


# end
print("\nInitial setup successful. You can log in with this information:")
print("Admin panel: http://ip/IBSng/admin")
print("Username: system")
print("Password: system\n")
