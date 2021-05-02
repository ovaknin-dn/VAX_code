#!/usr/bin/env python3
#import xml.dom.minidom
import xml.dom.minidom

from ncclient.xml_ import *
from ncclient import manager
from Requests_RPCs import *
from Netconf_filters import *
from Netconf_SR_filters import *
from config_SR import *
import logging
import json
import argparse
import ipaddress
import os
import re
import subprocess
import sys
from time import monotonic, sleep
from uuid import uuid4

import yaml
#global conn

try:
    import pexpect as pexpect
except ModuleNotFoundError as e:
    print("WARNING: missing python dependencies, please run the script with the '--install_prereq' flag")


def install_prereqs_and_delete():
    """
    - validate that the script is running with required privileges and correct options
    - install host requirements if the 'install_prereq' flag is set
    """
    if os.geteuid() != 0:
        exit("this script requires root privileges")
    if args.install_prereq:
        print("installing required apt packages")
        cmds = ["apt-get update",
                "apt-get install -y bridge-utils qemu-kvm libvirt-bin python python-netifaces vnc4server libyaml-dev "
                "python-yaml numactl libparted0-dev libpciaccess-dev libnuma-dev libyajl-dev libxml2-dev libglib2.0-dev"
                " libnl-3-dev python-pip python-dev libxml2-dev libxslt-dev python3-pip ethtool",
                "python3 -m pip install pexpect pyyaml"]
        for cmd in cmds:
            send_host_cmd(cmd, timeout=60 * 7, strict=False)
        exit(0)

def COMMIT(timeout):
    print("Commiting last changes")
    result_xml = activeSession.commit(confirmed=False, timeout=timeout)
    logging.info(result_xml)
    print(result_xml)

def EDIT_CONFIG(editFilter):
    result_xml = activeSession.edit_config(target='candidate', config=editFilter)
    logging.info(result_xml)
    result_xml = str(result_xml)
    parsedXML = xml.dom.minidom.parseString(result_xml)
    xml_pretty_str = parsedXML.toprettyxml()
    print(xml_pretty_str)

def GET_CONFIG(getFilter):
    result_xml = activeSession.get_config(source="running", filter=getFilter)
    result_xml = str(result_xml)
    parsedXML = xml.dom.minidom.parseString(result_xml)
    xml_pretty_str = parsedXML.toprettyxml()
    print(xml_pretty_str)


def connect(host, port, user, password):
    conn = manager.connect(host=host,
                           port=port,
                           username=user,
                           password=password,
                           timeout=600,
                           #device_params={'name': 'default'},
                           # hostkey_verify=False)
                           )
    return conn


parser = argparse.ArgumentParser(
    formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=50, width=150),
    description="""config/get-config/commit configurations using NetConf on hosts""")
parser.add_argument("--host_ip", type=host_ip_type, default=None, help="host ip to negotiate netconf with", required=True)
parser.add_argument("--user", type=str, default="iadmin", help="username to use for netconf connection")
parser.add_argument("--password", type=str, default="iadmin", help="password to use for netconf connection")
parser.add_argument("--port", type=int, default=830, help="port number to use for netconf connection")
parser.add_argument("--action", type=str, default="get-config", help="what action to initiate [get-config/edit-config/get(future)]")
parser.add_argument("--config_file", type=str, help="path to a local config file to paste into the device")
parser.add_argument("--install_prereq", action="store_true",
                    help="install required packages on the host. should only run once per host (default: False)")


if __name__ == '__main__':
    #LOG_FORMAT = '%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s'
    # logging.basicConfig(stream=sys.stdout,
    #                    level=logging.DEBUG, format=LOG_FORMAT)
    args = parser.parse_args()
    before = monotonic()
    # check user selections, fetch the needed info and handle prereq
    logging.Logger.debug("verifing and installing prereq")
    install_prereqs_and_delete()
    
    print("Initiating netconf session..")
    activeSession = connect(args.host, args.port, args.user, args.password)
    print("Netconf Session has successfully established.\nSending netconf RPC")
    
    if args.action
    GET_CONFIG(GET_CONFIG_ALL)
    EDIT_CONFIG(vax)
    COMMIT('300')
    print(f"script done in '{monotonic() - before}' seconds")


    """

    Following are the templates:
        "show config"                                            GET_CONFIG_ALL
        "show config protocols segmenet-routing mpls"            GET_SR_CONFIG         

    """

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    #result_xml = x.get_config(source="running", filter=GET_SR_CONFIG)
    #result_xml = str(result_xml)
    #xml = xml.dom.minidom.parseString(result_xml)
    #xml_pretty_str = xml.toprettyxml()
    #rint(xml_pretty_str)
    #result_xml = conn.get(netconf_filter5)
    # result_xml = x.edit_config(
    #   target='candidate', config=CONFIG_NC_TEST_PREFIX_LIST)
# RPC
    #DD = "clear-event-manager-policy-counters"
    #DD = 'clear-event-manager-policy-counters'
    #result_xml = x.rpc(DD)


# CONFIG
    #result_xml = x.edit_config(target='candidate', config=CONFIG_SR_SMALL_CONFIG)
    #logging.info(result_xml)
    #result_xml = str(result_xml)
    #xml = xml.dom.minidom.parseString(result_xml)
    #xml_pretty_str = xml.toprettyxml()
    #print(xml_pretty_str)
# commit
    #print("Commiting last changes")
    #result_xml = x.commit(confirmed=False, timeout='300')
    #logging.info(result_xml)
    #print(result_xml)

#############################################################################
# Description for NetConf template in Netconf_filter.py file
# ---------------------   PREFIX-LIST ----------------------------------------
# Prefix list called "NC_TEST" with 10 rules. Creation and deletion:
# CONFIG_NC_TEST_PREFIX_LIST
# DELETE_NC_TEST_PREFIX_LIST
#
# and get config for all existing prefix lists:
# GET_CONFIG_PREFIX_LIST_ALL
#
# ---------------------   ACCESS-LIST ----------------------------------------
# ACL called "NC_TEST_ACL" with 10 rules. Creation and deletion:
# CONFIG_NC_TEST_ACL
# DELETE_NC_TEST_ACL
#
# and get config for all existing prefix lists:
# ACL_GET_CONF
#
###
# ---------------------   BGP NEIGHOR  ----------------------------------------
# ACL called "NC_TEST_ACL" with 10 rules. Creation and deletion:
# CONFIG_NC_TEST_BGP_NEIGHBOR
# DELETE_NC_TEST_BGP_NEIGHBOR
#
# and get config for all existing prefix lists:
# ACL_GET_CONF
#
###
