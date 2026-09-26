# This file is part of 'NTLM Authorization Proxy Server'
# Copyright 2001 Dmitry A. Rozmanov <dima@xenon.spb.ru>
#
# NTLM APS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# NTLM APS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the sofware; see the file COPYING. If not, write to the
# Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#

hd = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F',]

def _ord(i):
    "accept both bytes elements (int) and str elements (char)"
    return i if isinstance(i, int) else ord(i)

#--------------------------------------------------------------------------------------------
def str2hex_num(data, delimiter=''):
    res = 0
    for i in data:
        res = res << 8
        res = res + _ord(i)
    return hex(res)

#--------------------------------------------------------------------------------------------
def str2hex(data, delimiter=''):
    res = ''
    for i in data:
        i = _ord(i)
        res = res + hd[i >> 4]
        res = res + hd[i & 0x0F]
        res = res + delimiter
    return res

#--------------------------------------------------------------------------------------------
def str2dec(data, delimiter=''):
    res = ''
    for i in data:
        res = res + '%3d' % _ord(i)
        res = res + delimiter
    return res


#--------------------------------------------------------------------------------------------
def hex2str(hex_str):
    res = bytearray()
    for i in range(0, len(hex_str), 2):
        res.append(hd.index(hex_str[i]) * 16 + hd.index(hex_str[i+1]))
    return bytes(res)

#--------------------------------------------------------------------------------------------
def str2prn_str(bin_str, delimiter=''):
    ""
    res = ''
    for i in bin_str:
        i = _ord(i)
        if i > 31: res = res + chr(i)
        else: res = res + '.'
        res = res + delimiter
    return res

#--------------------------------------------------------------------------------------------
def byte2bin_str(char):
    ""
    res = ''
    t = _ord(char)
    while t > 0:
        t1 = t // 2
        if t != 2 * t1: res = '1' + res
        else: res = '0' + res
        t = t1
    if len(res) < 8: res = '0' * (8 - len(res)) + res

    return res

#--------------------------------------------------------------------------------------------
def str2lst(data):
    res = []
    for i in data:
        res.append(_ord(i))
    return res

#--------------------------------------------------------------------------------------------
def lst2str(lst):
    return bytes(i & 0xFF for i in lst)

#--------------------------------------------------------------------------------------------
def int2chrs(number_int):
    ""
    return bytes([number_int & 0xFF, (number_int >> 8) & 0xFF])

#--------------------------------------------------------------------------------------------
def bytes2int(data):
    ""
    return _ord(data[1]) * 256 + _ord(data[0])

#--------------------------------------------------------------------------------------------
def int2hex_str(number_int16):
    ""
    res = '0x'
    ph = int(number_int16) // 256
    res = res + hd[ph >> 4]
    res = res + hd[ph & 0x0F]

    pl = int(number_int16) - (ph * 256)
    res = res + hd[pl >> 4]
    res = res + hd[pl & 0x0F]

    return res

#--------------------------------------------------------------------------------------------
def str2unicode(data):
    "converts ascii string to dumb unicode (utf-16le of the utf-8 bytes)"
    if isinstance(data, str):
        data = data.encode('utf-8')
    res = bytearray()
    for i in data:
        res.append(_ord(i))
        res.append(0)
    return bytes(res)

