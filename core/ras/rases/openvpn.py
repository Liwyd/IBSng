from core.ras.ras import Ras
from core.ras import ras_main
from core.ibs_exceptions import *
import socket
import time

def init():
    ras_main.getFactory().register(OpenVPNRas, "openvpn")


class OpenVPNRas(Ras):
    """
        OpenVPN NAS, spoken to by addons/openvpn/openvpn_agent.py.

        The agent authenticates users with RADIUS Access-Request (PAP) and
        drives accounting with Start/Stop/Alive Accounting-Requests built
        from OpenVPN hooks (auth-user-pass-verify, client-connect,
        client-disconnect) and the OpenVPN status file (interim updates).

        The RAS is looked up by packet source IP (rad_server), so the agent
        and this RAS must share an IP (normally 127.0.0.1).
    """
    type_attrs = {"openvpn_update_accounting_interval": 1, # minutes between
                                                              # Alive updates,
                                                              # also the
                                                              # isOnline
                                                              # freshness window
                   "openvpn_reonline_users": 1,
                   "openvpn_mgmt_socket": "/run/openvpn/ibsng.sock",
                   "openvpn_kill_timeout": 5
                  }

    def init(self):
        self.onlines = {} # port => {"username":,"in_bytes":,"out_bytes":,
                          #          "start_in_bytes":,"start_out_bytes":,
                          #          "last_update":}

####################################
    def killUser(self, user_msg):
        """
            disconnect the user through the OpenVPN management interface
            (unix socket, "kill <common_name>" command)
        """
        self.__killByUsername(self.__getUsernameFromUserMsg(user_msg))

    def __killByUsername(self, username):
        sock_path = self.getAttribute("openvpn_mgmt_socket")
        timeout = int(self.getAttribute("openvpn_kill_timeout"))
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                sock.connect(sock_path)
                sock.sendall(b"kill %s\n" % username.encode("utf-8"))
                data = b""
                while b"\n" not in data:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            finally:
                sock.close()
            reply = data.decode("utf-8", "replace").strip()
            if "ERROR" in reply:
                self.toLog("killUser(%s): management socket said: %s" % (username, reply), LOG_ERROR)
        except:
            logException(LOG_ERROR)

    def __getUsernameFromUserMsg(self, user_msg):
        """
            return (username) of logged on user
        """
        instance_info = user_msg["user_obj"].getInstanceInfo(user_msg["instance"])
        return instance_info["attrs"]["username"]

####################################
    def getInOutBytes(self, user_msg):
        try:
            port = user_msg["port"]
            if port in self.onlines:
                return (self.onlines[port]["in_bytes"], self.onlines[port]["out_bytes"],
                        self.onlines[port].get("in_rate", 0), self.onlines[port].get("out_rate", 0))
            else:
                return (0, 0, 0, 0)
        except:
            logException(LOG_ERROR)
            return (-1, -1, -1, -1)

####################################
    def isOnline(self, user_msg):
        return user_msg["port"] in self.onlines and \
               self.onlines[user_msg["port"]]["last_update"] >= \
               time.time() - int(self.getAttribute("openvpn_update_accounting_interval")) * 60

####################################
    def __addUniqueIdToRasMsg(self, ras_msg):
        ras_msg["unique_id"] = "port"
        ras_msg["port"] = str(ras_msg.getRequestPacket()["NAS-Port"][0])

####################################
    def handleRadAuthPacket(self, ras_msg):
        self.__addUniqueIdToRasMsg(ras_msg)
        ras_msg.setInAttrs({"User-Name": "username"})
        ras_msg.setInAttrsIfExists({
            "User-Password": "pap_password",
            "CHAP-Password": "chap_password",
            "MS-CHAP-Response": "ms_chap_response",
            "MS-CHAP2-Response": "ms-chap2-response",
            "Calling-Station-Id": "station_ip",
            "Framed-IP-Address": "remote_ip"
        })

        if ras_msg["port"] in self.onlines:
            self.onlines[ras_msg["port"]]["in_bytes"] = 0
            self.onlines[ras_msg["port"]]["out_bytes"] = 0

        ras_msg.getReplyPacket()["Acct-Interim-Interval"] = \
            int(self.getAttribute("openvpn_update_accounting_interval")) * 60

        ras_msg.setAction("INTERNET_AUTHENTICATE")

####################################
    def handleRadAcctPacket(self, ras_msg):
        status_type = ras_msg.getRequestAttr("Acct-Status-Type")[0]
        self.__addUniqueIdToRasMsg(ras_msg)

        if status_type == "Start":
            ras_msg.setInAttrs({"User-Name": "username",
                                "Acct-Session-Id": "session_id"})
            ras_msg.setInAttrsIfExists({"Framed-IP-Address": "remote_ip"})
            ras_msg["start_accounting"] = True
            ras_msg["update_attrs"] = ["remote_ip", "start_accounting"]

            self.__addInOnlines(ras_msg)

            ras_msg.setAction("INTERNET_UPDATE")

        elif status_type == "Stop":
            ras_msg.setInAttrs({"User-Name": "username",
                                "Acct-Session-Id": "session_id"})
            ras_msg.setInAttrsIfExists({
                "Framed-IP-Address": "remote_ip",
                "Acct-Output-Octets": "in_bytes",
                "Acct-Input-Octets": "out_bytes",
                "Acct-Terminate-Cause": "terminate_cause"
            })

            if ras_msg["port"] in self.onlines:
                if ras_msg.hasAttr("in_bytes"):
                    self.onlines[ras_msg["port"]]["in_bytes"] = ras_msg["in_bytes"]
                if ras_msg.hasAttr("out_bytes"):
                    self.onlines[ras_msg["port"]]["out_bytes"] = ras_msg["out_bytes"]

            ras_msg.setAction("INTERNET_STOP")

        elif status_type in ("Alive", "Interim-Update"):
            # dictionary lists both names for status type 3
            if not self.isUserOnline(ras_msg) and int(self.getAttribute("openvpn_reonline_users")):
                self.tryToReOnline(ras_msg)
                self.toLog("handleRadAcctPacket: Alive received, but user is not in Onlines", LOG_ERROR)
            else:
                self.__updateInOnlines(ras_msg)

        else:
            self.toLog("handleRadAcctPacket: invalid status_type %s" % status_type, LOG_ERROR)

####################################
    def populateReOnlineRasMsg(self, ras_msg):
        Ras.populateReOnlineRasMsg(self, ras_msg)
        ras_msg.setInAttrsIfExists({"Calling-Station-Id": "station_ip"})

    def tryToReOnlineResult(self, ras_msg, auth_success):
        if auth_success:
            self.__addInOnlines(ras_msg)
        else:
            # auth failed - kick the tunnel
            self.toLog("tryToReOnlineResult: kill %s on unsuccessful re-online" % ras_msg["username"], LOG_ERROR)
            self.__killByUsername(ras_msg["username"])


####################################
    def __addInOnlines(self, ras_msg):
        pkt = ras_msg.getRequestPacket()
        if "Acct-Output-Octets" in pkt:
            start_in_bytes = pkt["Acct-Input-Octets"][0]
            start_out_bytes = pkt["Acct-Output-Octets"][0]
        else:
            start_in_bytes = 0
            start_out_bytes = 0

        self.onlines[ras_msg["port"]] = {"username": ras_msg["username"],
                                         "in_bytes": 0,
                                         "out_bytes": 0,
                                         "in_rate": 0,
                                         "out_rate": 0,
                                         "start_in_bytes": start_in_bytes,
                                         "start_out_bytes": start_out_bytes,
                                         "last_update": time.time()}

    def __updateInOnlines(self, ras_msg):
        if ras_msg["port"] in self.onlines:
            in_bytes = ras_msg.getRequestAttr("Acct-Output-Octets")[0]
            out_bytes = ras_msg.getRequestAttr("Acct-Input-Octets")[0]
            duration = max(1, time.time() - self.onlines[ras_msg["port"]]["last_update"])

            self.onlines[ras_msg["port"]]["in_rate"] = \
                (in_bytes - self.onlines[ras_msg["port"]]["in_bytes"]) / duration
            self.onlines[ras_msg["port"]]["out_rate"] = \
                (out_bytes - self.onlines[ras_msg["port"]]["out_bytes"]) / duration

            self.onlines[ras_msg["port"]]["in_bytes"] = in_bytes
            self.onlines[ras_msg["port"]]["out_bytes"] = out_bytes
            self.onlines[ras_msg["port"]]["last_update"] = time.time()
        else:
            self.toLog("Update accounting called for %s,%s while he's NOT on my online list" %
                       (ras_msg.getRequestAttr("User-Name")[0], ras_msg["port"]), LOG_ERROR)
