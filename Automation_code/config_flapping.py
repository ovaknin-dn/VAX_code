#!/usr/bin/python3
from netmiko import ConnectHandler
import sys,os
import time
dn = {
    "device_type": "cisco_ios",
    "host": "100.64.14.4",
    "username": "dnroot",
    "password": 'dnroot',
}
# Show command that we execute.
mgmtInterfaces = """top
    interfaces mgmt0
    admin-state enabled
    ipv4-address 100.64.14.4/20
    ipv6-address dhcpv6
  !
!
"""
mgmtStatic = """ top
    system management
    vrf mgmt0
      static
        address-family ipv4
          route 0.0.0.0/0 next-hop 100.64.15.254
        !
      !
    !
  !
  !
  """
exitLOOP = True
while exitLOOP:
  flag = 0
  try:
      with ConnectHandler(**dn) as net_connect:
          print('Starting load-factory override\n\n')
          out = net_connect.send_command_timing('configure')
          print(out)
          out = net_connect.send_command_timing('load override factory-default')
          print(out)
          time.sleep(60)
          out = net_connect.send_command_timing(mgmtInterfaces)
          print(out)
          out = net_connect.send_command_timing(mgmtStatic)
          print(out)
          out = net_connect.send_command_timing('commit')
          print(out)
          time.sleep(300)
          #exitLOOP = net_connect.send_command_timing('configure')
          exitLOOP = net_connect.check_config_mode()
          #print(exitLOOP)
          print('Finished load-factory override')
  except Exception as e:
      print(e)
      exitLOOP = False
  try:
      with ConnectHandler(**dn) as net_connect:
          print('Starting rollback1 ')
          out = net_connect.send_command_timing('configure')
          print(out)
          out = net_connect.send_command_timing('rollback 1')
          print(out)
          time.sleep(60)
          out = net_connect.send_command_timing('commit')
          print(out)
          time.sleep(180)
          #exitLOOP = net_connect.send_command_timing('configure')
          exitLOOP = net_connect.check_config_mode()
          print('Finished rollback1 ')
      flag += 1
      print(f"ran for {flag} times until now..")
      os.system(f"echo 'ran for {flag} times until now..'>> config_flapping.log")
  except Exception as e:
      print(e)
      exitLOOP = False
