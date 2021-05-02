#!/usr/bin/env python3
import argparse
import ipaddress
import os
import re
import subprocess
import sys
from time import monotonic, sleep
from uuid import uuid4

import yaml

try:
    import pexpect as pexpect
except ModuleNotFoundError as e:
    print("WARNING: missing python dependencies, please run the script with the '--install_prereq' flag")


def send_host_cmd(cmd, strict=True, timeout=30, return_status_code=False, **kwargs) -> str or int:
    """
    send a command to the local host and wait for the process for exit.

    :param strict: if True, stop execution on failure
    :param timeout: time to wait for process to exit
    :param return_status_code: return status code instead of stdout
    """
    child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, **kwargs)
    status_code = child.wait(timeout)
    if strict and status_code != 0:
        print(f"ERROR: failed to execute command '{cmd}' on host")
        exit(1)
    if return_status_code:
        return status_code
    # noinspection PyUnresolvedReferences
    return child.communicate()[0].decode().strip()


class InteropEnv:  # TODO: move the images files to a more stable location, not a lab server
    # NOTE: if you change the images, remember to also change the description in the 'help' menu at the bottom of this file
    CISCO_IMAGE = {
        'src': "kvm95:/var/lib/libvirt/images/cisco_vm_base.qcow2",
        'user': "dn",
        'pass': "drive1234!",
        'local_dir': "/var/lib/libvirt/images/",
        'local_name': 'cisco_vm_base.qcow2',
        'image_size_gb': 6.2,
        'memory_kb': 8388608
    }
    CISCO_IMAGE['local_path'] = os.path.join(CISCO_IMAGE['local_dir'], CISCO_IMAGE['local_name'])
    JUNIPER_IMAGE = {
        'src': "dn111:/opt/vmx/vmx-bundle-20.4R1.12.tgz",
        'user': "dn",
        'pass': "drive1234!",
        'local_dir': "/var/lib/libvirt/images/",
        'local_name': 'vmx-bundle-20.4R1.12.tgz',
        're_image_name': 'junos-vmx-x86-64-20.4R1.12.qcow2',
        'license': [
            "19 222 Ni LONG NORMAL STANDALONE AGGR 1_KEYS INFINITE_KEYS 3 FEB 2021 0 0 4 MAR 2022 23 59 NiL SLM_CODE DEMO NiL NiL Ni NiL NiL 15_MINS NiL 0 fW5lRxt9Pg8W25TAFQhPcDG+uv5yCd+507k2il0nIixUZ86ZO0P7MFm7VB1LKmlqWb1nV/rissgJyMKWruPc7xRTjln60mt4n5+2MqdCsr/b3+HOEquRRiLJpawUgIpTl8aK+bVsTCaLreB+zpmNRnzfVbQZWXrEs6mmTF8/ZwY+pGbVTbMl1w+WOJM1MsmW+ZlSHdAiQxZihxVBZIkIH7jk2tT8LeniXQvIJexUkHFXOFxcP06kJQ5grQiJxA18loQ11CWLzOLU6byIW1bC1rBfRKTOf15AN9RTKdJbSgYBLIoRpo/i5fk+60rP7ePK8/ssL4Xsodwanb5wChzSo9PVdaGf26Stqf/f6XJnSg9qTjmWBnf+yNjr8cokt4A0CafIC4Yl6USpeTxAWoSG+WDwTZ13QK4huQGPW9xh0Ymujx4N0OqnPDP1Digfi5T3y0OVOPHrnBJybTCbi/iehW+LuwlJJDWNhR8645CHG+UIeodi8Zwe/BWDc0AtLYOx/duSTrIi/7Wu4k4ovE3iubO+4+2WGNkWJYEr3A/ntpu5xS6cnn6DZ+PKSBqWeULCBQRSQ0IyC4MJBQRSQ0IyBgEBBwEBBCU4YjFiNmYxZC0zNzY5LTRmNGUtYjM4Ny0zNGUzMmVlOTYzYmQACAEBCUClydIpUZi6n8jzILOrVPag59XNDAizpYck68gc4uLfRITzGmdQTKfa9U1K8BGjzfbX0S4wCDZhm4lh55efpLXVCoIOMIIBCgKCAQEA2OMgESQh1fz4LjXZ0SmDsrPGJ2cB5zU4CPsQmQj0FjnjUYfF41nDGO6O4mpIny5WTzFJYSp61719oZyDEVsJYZwnqK3NzyswNBVj3CqSHx3HpKCu1nqAN1sC79hbxa3LsbvGa2522jtMzhrd7F3MdycGewa2O060rrBz9ZroxirqH6Zx4jmzFRJbgZX7UUOJswW3b5cTKlOyX/YYl1rQIoaZ+f1YtEaIRHQ8j9j8Xn/G4AT1XjQFOH9Yfo39PPERGr1sCGOIlKpYWZJhP6L3HqIMF22tsAWJLVkOIPCuI/PZpk5VMmYZoF3KMdo5kSfATgotW6ufhqSNSbhR6nu7iwIDAQABBCU4YjFiNmYxZC0zNzY5LTRmNGUtYjM4Ny0zNGUzMmVlOTYzYmQABwEBDIIAj/0GXRSG4RZgcziqdmNuGArFJszXA01vxuGTUS1dUjdf0PKBt0rp/92L0SoOPcTT/euVdaFJICecqJh5iqMBAEtLAw2fCeVHWSQOQdyj3dcthKhBU9krhybd9MQ+6Zsi1TUReOKqLiTuum7p6IDyVHqIISAfEhoE7j2A446m1JfJON08LujErm7c2f9PFYI0FMbjocBTuotH2gqaemRPGdqasYEP2aPrOdj/bQeGErw+Y2WULrkPYxQsiLDwTzcnEczDmmRHq0hDvCdCAs2bJ8q0CFezNXWJRSHBqd4ZRWvfg8TCCyKFrFSKqLlH+SAgzqW+D0Njf7kqv87hiVz/QwAAAr8=#KeyType=Commercial#AID=7a02c0aa-c4f3-494e-aed5-c53dc774b2b2 SIGN=0728059BAAAB64401E8AAD9502F7E3056A047FA9DBD81713805AE0B146D580BC1AA683E3059F099A1A9E",
            "19 166 Ni LONG NORMAL STANDALONE AGGR 100_KEYS INFINITE_KEYS 3 FEB 2021 0 0 4 MAR 2022 23 59 NiL SLM_CODE DEMO NiL NiL Ni NiL NiL 15_MINS NiL 0 M0xg2NRsCiPg1C6bDOnIqZeTeatA/qWNgvcEidfCGF6Mc7y+9LkJBU/nKwqHUZZ0dM/KsfU2RJ/ybkCGltwVNR/rxdUgc2kQnTONbK4rEtIuMaYRXlmbAoYv//odQbvmvyyQFW/vekVp7ENJHlpBpRQkEcNDOL4npcncXhkz/7d+qi1Du8myEFm8tw0jW/cqYbX4ARgW3y7v2HZ8OofSR89xd3DK/6TplRgR8l2vixBkqpNxac2YGwsK8m0U8wUTyBL0Bs3jt8EddwqJ1GzUJQaiik3nzAZ4YtrTKFPi3T5FSMRabLTCAjz7CWyZnhflmSreSOuEM0kCk6K5BS1FjBIXJ/+AMWtR1S9mFGsA76Z+jnkhfnMO+w/Bdg7kOE72OAdR2/acMURcCawR+Qj+3f0JeYYQuM1wEsZTCZShVZrmUDAQXvq+qJvW5kEHdvK8YIO1rWpC/U+5hBG2RyLnEaAqS2Ec4v1mTZ9LUCBsJB75B5OLVF7OSot2iiUB8n/9wGc7R/MZLWySrif+ub2ILuoU3pybxs44hA6fa5+ZQ3XjYYC/8ivG+gL/fXnp9cnJBQRSQ0IyC4MJBQRSQ0IyBgEBBwEBBCU4YjFiNmYxZC0zNzY5LTRmNGUtYjM4Ny0zNGUzMmVlOTYzYmQACAEBCUClydIpUZi6n8jzILOrVPag59XNDAizpYck68gc4uLfRITzGmdQTKfa9U1K8BGjzfbX0S4wCDZhm4lh55efpLXVCoIOMIIBCgKCAQEA2OMgESQh1fz4LjXZ0SmDsrPGJ2cB5zU4CPsQmQj0FjnjUYfF41nDGO6O4mpIny5WTzFJYSp61719oZyDEVsJYZwnqK3NzyswNBVj3CqSHx3HpKCu1nqAN1sC79hbxa3LsbvGa2522jtMzhrd7F3MdycGewa2O060rrBz9ZroxirqH6Zx4jmzFRJbgZX7UUOJswW3b5cTKlOyX/YYl1rQIoaZ+f1YtEaIRHQ8j9j8Xn/G4AT1XjQFOH9Yfo39PPERGr1sCGOIlKpYWZJhP6L3HqIMF22tsAWJLVkOIPCuI/PZpk5VMmYZoF3KMdo5kSfATgotW6ufhqSNSbhR6nu7iwIDAQABBCU4YjFiNmYxZC0zNzY5LTRmNGUtYjM4Ny0zNGUzMmVlOTYzYmQABwEBDIIAj/0GXRSG4RZgcziqdmNuGArFJszXA01vxuGTUS1dUjdf0PKBt0rp/92L0SoOPcTT/euVdaFJICecqJh5iqMBAEtLAw2fCeVHWSQOQdyj3dcthKhBU9krhybd9MQ+6Zsi1TUReOKqLiTuum7p6IDyVHqIISAfEhoE7j2A446m1JfJON08LujErm7c2f9PFYI0FMbjocBTuotH2gqaemRPGdqasYEP2aPrOdj/bQeGErw+Y2WULrkPYxQsiLDwTzcnEczDmmRHq0hDvCdCAs2bJ8q0CFezNXWJRSHBqd4ZRWvfg8TCCyKFrFSKqLlH+SAgzqW+D0Njf7kqv87hiVz/QwAAAr8=#KeyType=Commercial#AID=7a02c0aa-c4f3-494e-aed5-c53dc774b2b2 SIGN=07280B1E5772C3B7983CE8194E071E0A1DAD00F3AA418B7DD1DAC214CA5DBED42343C702630B8EB17AC6"
        ],
        'image_size_gb': 12,
        'vcp_memory_mb': 2048,
        'vfp_memory_mb': 4096,
    }
    JUNIPER_IMAGE['local_path'] = os.path.join(JUNIPER_IMAGE['local_dir'], JUNIPER_IMAGE['local_name'])

    def __init__(self, host_mgmt_br, free_cpus, vm_name, vm_type, interfaces, mgmt_ip, mgmt_gw, cli_config):
        self.mgmt_ip = mgmt_ip or '1.2.3.4/20'  # TODO: fix juniper installation when no mgmt_ip provided
        self.mgmt_gw = mgmt_gw
        self.cli_config = cli_config or ""
        self.host_mgmt_br = host_mgmt_br
        self.free_cpus = iter(free_cpus)
        self.vm_name = vm_name
        self.vm_type = vm_type
        self.interfaces = interfaces or []

        self._mac_addr_count = 0
        self.juniper_cpus = []

    def __enter__(self):
        self.define_networks()
        self.fetch_images()
        if self.vm_type == 'cisco':
            self.config_and_start_cisco_vm()
        else:
            self.config_and_start_juniper_vm()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.vm_type == 'cisco':
            self.wait_for_cisco_boot_and_set_base_config()
        else:
            self.wait_for_juniper_boot_and_set_base_config()

    def __call__(self, *args, **kwargs):
        """
        the group-creation flow starts here (see __enter__ and __exit__ methods)
        """
        with self:
            pass

    def define_networks(self):
        """
        define all of the virsh networks, as listed in the 'self.interfaces' dict
        """
        networks = set()
        for interface in self.interfaces:
            if_type, if_name = interface.split(':', 1)
            if if_type == 'net':
                networks.add(if_name)
        existing_networks = send_host_cmd('virsh net-list --all --name').splitlines()
        for network in networks:
            if network not in existing_networks:
                print(f"creating virsh network {network}")
                self.create_virsh_network(network)

    def wait_for_juniper_boot_and_set_base_config(self):
        """
        wait for all juniper devices to boot and set:
        - paste basic CLI config for management
        - bind bridge interfaces using the `vmx.sh` script
        - bind CPUs to the VCP and VFP vms
        """
        child = self.wait_for_juniper_boot()
        sleep(20)  # if configuring too fast, configuration will not be applied
        self.set_juniper_base_config(child, self.mgmt_ip)
        self._install_juniper_license(child)
        if self.interfaces:
            self.bind_juniper_dev_interfaces()
        self.set_juniper_cpu_binding()

    def wait_for_cisco_boot_and_set_base_config(self):
        """
        wait for all cisco devices to boot and paste basic CLI config for management
        """
        self.wait_for_cisco_boot()
        self.set_cisco_base_config(self.mgmt_ip)

    def config_and_start_juniper_vm(self):
        """
        - extract juniper image
        - build the vm configuration files and install using `vmx.sh` script
        - update the VFP vm interfaces binding to make them persistent after host reboot
        """
        self.juniper_cpus = [next(self.free_cpus) for _ in range(4)]
        cloned_image = self.clone_juniper_vm()
        self.configure_juniper_vm(cloned_image, self.juniper_cpus)

        retries = 3
        for i in range(retries):  # installation randomly fails, so try again
            if self.install_juniper_vm():
                break
            if i < retries:
                print(f"installation failed for juniper vm '{self.vm_name}', retrying in 5 seconds")
                sleep(5)
            else:
                exit(f"ERROR: failed to install juniper vm '{self.vm_name}' after {retries} retries")
        # self.update_vfp_interfaces(self.vm_name)

    def config_and_start_cisco_vm(self):
        """
        - copy cisco image file
        - generate an XML file and define it using `virsh define`
        - start VM
        """
        cloned_image = self.clone_cisco_vm()
        self.configure_cisco_vm(cloned_image, [next(self.free_cpus) for _ in range(2)])
        self.start_cisco_vm()

    def fetch_images(self):
        """
        fetch cisco and juniper images from the remote host if they are not found locally.
        """
        if self.vm_type == 'cisco':
            self.get_cisco_image()
        if self.vm_type == 'juniper':
            self.get_juniper_image()

    @property
    def mac_addr_count(self):
        """
        make sure mac addresses are unique within the group
        """
        self._mac_addr_count += 1
        return str(self._mac_addr_count).zfill(2)

    def clone_juniper_vm(self):
        """
        extract the image tar to a folder with the VM name.
        """
        local_dir = self.JUNIPER_IMAGE['local_dir']
        new_path = os.path.join(local_dir, self.vm_name)
        print(f"cloning juniper vm to local folder '{new_path}'")
        send_host_cmd(f"mkdir {new_path}")
        send_host_cmd(f"tar -xvf {self.JUNIPER_IMAGE['local_path']} -C {new_path}", timeout=60 * 7)
        # mv files from the internal dir 'vmx' to the main folder
        send_host_cmd(f"mv {os.path.join(new_path, 'vmx', '*')} {new_path}")
        send_host_cmd(f"rm -rf {os.path.join(new_path, 'vmx')}")
        return new_path

    def clone_cisco_vm(self):
        """
        copy the base image file and set the vm name as the file name.
        """
        local_path = self.CISCO_IMAGE['local_path']
        new_path = os.path.join(self.CISCO_IMAGE['local_dir'], self.vm_name + ".qcow2")
        print(f"cloning cisco vm from '{local_path}' to '{new_path}'")
        send_host_cmd(f"cp {local_path} {new_path}", timeout=60 * 3)
        return new_path

    def get_cisco_image(self):
        self.get_image(self.CISCO_IMAGE)

    def get_juniper_image(self):
        self.get_image(self.JUNIPER_IMAGE)

    def get_image(self, image_info):
        """
        use 'rsync' to fetch a cisco/juniper image from a remote location, if the image is not found locally.
        """
        src = image_info['src']
        user = image_info['user']
        passw = image_info['pass']
        local_path = image_info['local_path']
        copy_cmd = (f"rsync -e 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no' {user}@{src} "
                    f"{local_path}")
        if os.path.exists(local_path):
            print(f"using image at local path '{local_path}' for vm creation")
            return
        print(f"copying image '{src}' to local path '{local_path}'")
        child = pexpect.spawn(copy_cmd)
        child.expect("password:")
        child.sendline(passw)
        child.wait()

    def configure_juniper_vm(self, image_path, cpus, traffic_interfaces_count=2):
        """
        generate the `vmx.conf` and the `vmx-junosdev.conf` files that are needed for the VM installation
        """
        vm_id = str(cpus[0]).zfill(2)
        traffic_interfaces = '\n'.join([f"""   - interface            : ge-0/0/{i}
     mac-address          : "02:06:0A:0E:{vm_id}:{self.mac_addr_count}"
     description          : "ge-0/0/{i} interface"
""" for i in range(traffic_interfaces_count)])
        config_format = f"""##############################################################
#
#  vmx.conf
#  Config file for vmx on the hypervisor.
#  Uses YAML syntax.
#  Leave a space after ":" to specify the parameter value.
#
##############################################################

---
#Configuration on the host side - management interface, VM images etc.
HOST:
    identifier                : {self.vm_name[-6:]}   # Maximum 6 characters
    host-management-interface : {self.host_mgmt_br}
    routing-engine-image      : "{image_path}/images/{self.JUNIPER_IMAGE['re_image_name']}"
    routing-engine-hdd        : "{image_path}/images/vmxhdd.img"
    forwarding-engine-image   : "{image_path}/images/vFPC-20201209.img"

---
#External bridge configuration
BRIDGES:
    - type  : external
      name  : {self.host_mgmt_br}                  # Max 10 characters

---
#vRE VM parameters
CONTROL_PLANE:
    vcpus       : 1
    memory-mb   : {self.JUNIPER_IMAGE['vcp_memory_mb']}
    console_port: 86{vm_id}

    interfaces  :
      - type      : static
        ipaddr    : 10.102.144.94
        macaddr   : "0A:00:DD:C0:DF:{vm_id}"

---
#vPFE VM parameters
FORWARDING_PLANE:
    memory-mb   : {self.JUNIPER_IMAGE['vfp_memory_mb']}
    vcpus       : 3
    console_port: 87{vm_id}
    device-type : virtio

    interfaces  :
      - type      : static
        ipaddr    : 10.102.144.98
        macaddr   : "0A:00:DD:C0:DE:{vm_id}"

---
#Interfaces
JUNOS_DEVICES:
{traffic_interfaces}
"""
        junosdev_format = 'interfaces :\n' + '\n'.join([f"""
     - link_name  : vmx_link{i}
       mtu        : 9000
       endpoint_1 :
         - type        : junos_dev
           vm_name     : {self.vm_name}
           dev_name    : ge-0/0/{i}
       endpoint_2 :
         - type        : bridge_dev
           dev_name    : {traffic_br.split(':', 1)[1]}
           """ for i, traffic_br in enumerate(self.interfaces)])
        print(f"writing 'vmx.conf' file for juniper vm '{self.vm_name}'")
        conf_path = os.path.join(image_path, 'config', 'vmx.conf')
        with open(conf_path, 'w') as f:
            f.write(config_format)

        print(f"writing 'vmx-junosdev.conf' file for juniper vm '{self.vm_name}'")
        conf_path = os.path.join(image_path, 'config', 'vmx-junosdev.conf')
        with open(conf_path, 'w') as f:
            f.write(junosdev_format)

    def configure_cisco_vm(self, image_path, cpus, traffic_interfaces_count=2):
        """
        build cisco VM XML file and define it using `virsh define` and configure it to auto-start on next host boot.
        """
        cpus = [str(_cpu) for _cpu in cpus]
        vm_id = str(cpus[0]).zfill(2)
        traffic_interfaces = ""
        for host_interface in self.interfaces:
            if_type, if_name = host_interface.split(':', 1)
            xml_if_type = 'bridge' if if_type == 'br' else 'network'
            traffic_interfaces += f"""    <interface type='{xml_if_type}'>
          <mac address='52:54:00:03:{vm_id}:{self.mac_addr_count}'/>
          <source {xml_if_type}='{if_name}'/>
          <model type='e1000'/>
        </interface>\n"""

        vcpus = '\n'.join([f"        <vcpupin vcpu='{i}' cpuset='{cpu}'/>" for i, cpu in enumerate(cpus)])
        vm_uuid = uuid4()
        xml_format = f"""<domain type='kvm'>
      <name>{self.vm_name}</name>
      <uuid>{vm_uuid}</uuid>
      <memory unit='KiB'>{self.CISCO_IMAGE['memory_kb']}</memory>
      <currentMemory unit='KiB'>{self.CISCO_IMAGE['memory_kb']}</currentMemory>
      <memoryBacking>
        <hugepages/>
      </memoryBacking>
      <vcpu placement='static' cpuset='{','.join(cpus)}'>{len(cpus)}</vcpu>
      <cputune>
{vcpus}
        <emulatorpin cpuset='{','.join(cpus)}'/>
      </cputune>
      <resource>
        <partition>/machine</partition>
      </resource>
      <os>
        <type arch='x86_64' machine='pc-i440fx-xenial'>hvm</type>
        <boot dev='hd'/>
      </os>
      <features>
        <acpi/>
        <apic/>
        <vmport state='off'/>
      </features>
      <cpu mode='host-model'>
        <model fallback='allow'/>
      </cpu>
      <clock offset='utc'>
        <timer name='rtc' tickpolicy='catchup'/>
        <timer name='pit' tickpolicy='delay'/>
        <timer name='hpet' present='no'/>
      </clock>
      <on_poweroff>destroy</on_poweroff>
      <on_reboot>restart</on_reboot>
      <on_crash>destroy</on_crash>
      <pm>
        <suspend-to-mem enabled='no'/>
        <suspend-to-disk enabled='no'/>
      </pm>
      <devices>
        <emulator>/usr/bin/kvm-spice</emulator>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='{image_path}'/>
          <target dev='hda' bus='ide'/>
          <address type='drive' controller='0' bus='0' target='0' unit='0'/>
        </disk>
        <controller type='usb' index='0' model='ich9-ehci1'>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x0b' function='0x7'/>
        </controller>
        <controller type='usb' index='0' model='ich9-uhci1'>
          <master startport='0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x0b' function='0x0' multifunction='on'/>
        </controller>
        <controller type='usb' index='0' model='ich9-uhci2'>
          <master startport='2'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x0b' function='0x1'/>
        </controller>
        <controller type='usb' index='0' model='ich9-uhci3'>
          <master startport='4'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x0b' function='0x2'/>
        </controller>
        <controller type='pci' index='0' model='pci-root'/>
        <controller type='ide' index='0'>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x1'/>
        </controller>
        <controller type='virtio-serial' index='0'>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x0a' function='0x0'/>
        </controller>
        <interface type='bridge'>
          <mac address='52:54:00:90:{vm_id}:{self.mac_addr_count}'/>
          <source bridge='{self.host_mgmt_br}'/>
          <model type='e1000'/>
          <alias name='net0'/>
        </interface>
        <interface type='bridge'>
          <mac address='52:54:00:90:{vm_id}:{self.mac_addr_count}'/>
          <source bridge='{self.host_mgmt_br}'/>
          <model type='e1000'/>
          <alias name='net0'/>
        </interface>
        <interface type='bridge'>
          <mac address='52:54:00:90:{vm_id}:{self.mac_addr_count}'/>
          <source bridge='{self.host_mgmt_br}'/>
          <model type='e1000'/>
          <alias name='net0'/>
        </interface>
    {traffic_interfaces}
        <serial type='pty'>
          <target port='0'/>
        </serial>
        <console type='pty'>
          <target type='serial' port='0'/>
        </console>
        <channel type='spicevmc'>
          <target type='virtio' name='com.redhat.spice.0'/>
          <address type='virtio-serial' controller='0' bus='0' port='1'/>
        </channel>
        <memballoon model='virtio'>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x0c' function='0x0'/>
        </memballoon>
      </devices>
    </domain>
    """
        xml_path = f'/tmp/cisco_xml_{vm_uuid}'

        print(f"writing virsh-xml to '{xml_path}'")
        with open(xml_path, 'w') as f:
            f.write(xml_format)

        print(f"defining xml as vm with name '{self.vm_name}'")
        send_host_cmd(f"virsh define {xml_path}")

        print(f"configuring '{self.vm_name}' to autostart on server boot")
        send_host_cmd(f"virsh autostart {self.vm_name}")

    def start_cisco_vm(self):
        print(f"starting cisco vm '{self.vm_name}'")
        send_host_cmd(f"virsh start {self.vm_name}")

    def install_juniper_vm(self):
        """
        use `vmx.sh` to install the vm and configure it to auto-start on next host boot.
        """
        local_path = os.path.join(self.JUNIPER_IMAGE['local_dir'], self.vm_name)
        print(f"installing and starting juniper vm '{self.vm_name}'")
        status = send_host_cmd("./vmx.sh --install", cwd=local_path, timeout=60 * 7, strict=False,
                               return_status_code=True)
        if status != 0:
            return False
        print(f"configuring vms of '{self.vm_name}' to autostart on server boot")
        for name in (f"vcp-{self.vm_name}", f"vfp-{self.vm_name}"):
            send_host_cmd(f"virsh autostart {name}")
        return True

    # def update_vfp_interfaces(self, vm_name):
    #     """
    #     update the VFP vm virsh configuration, so that the bridge binding will be persistent after reboot.
    #     this is done by:
    #     - read existing virsh-XML configuration and extracting the 'network' interfaces configuration
    #     - detach the 'network' interfaces
    #     - attach new 'bridge' interfaces using the same mac-address
    #     """
    #     fe_vm_name = f"vfp-{vm_name}"
    #     print(f"replacing 'network' interfaces configuration with 'bridge' interfaces in vm '{fe_vm_name}'")
    #     vm_xml = send_host_cmd(f"virsh dumpxml {fe_vm_name}")
    #     network_interfaces = re.findall(r"<interface type='network'>[\s\S]+?</interface>", vm_xml)
    #     for interface in network_interfaces:
    #         mac = re.search(r"mac address='(.*)'", interface).group(1)
    #         send_host_cmd(f'virsh detach-interface {fe_vm_name} network --mac "{mac}" --config')
    #         bridge_xml = re.sub(r'<source network=.*', rf"<source bridge='{self.traffic_br}'/>",
    #                             interface).replace("type='network'", "type='bridge'")
    #         xml_path = f'/tmp/{fe_vm_name}_br.xml'
    #         with open(xml_path, 'w') as f:
    #             f.write(bridge_xml)
    #         send_host_cmd(f"virsh attach-device {fe_vm_name} {xml_path} --config")

    def create_virsh_network(self, network_name):
        """
        create a virsh network using virsh net-define
        """
        xml_content = f"""<network>
  <name>{network_name}</name>
</network>"""
        xml_file_path = '/tmp/net_xml.xml'
        with open(xml_file_path, 'w') as f:
            f.write(xml_content)
        send_host_cmd(f"virsh net-define {xml_file_path}")
        send_host_cmd(f"virsh net-start {network_name}")
        send_host_cmd(f"virsh net-autostart {network_name}")

    def _is_cisco_booted(self, child):
        """
        cisco is considered booted when:
        - login is successful
        - the CLI 'configure' command is sent without showing a warning
        """
        child.sendline('\n\r')
        child.expect(r'Username:|\[no\]|.*#', timeout=5)
        if "Username:" in child.after.decode():
            child.sendline("dn")
            child.expect("Password:")
            child.sendline("drive1234!")

        child.sendline('configure')
        child.expect(r'\[no\]|.*#')
        if "(config" in child.after.decode():
            return True
        if "[no]" in child.after.decode():
            child.sendline("no")

    def _is_juniper_booted(self, child):
        """
        juniper is considered booted when 'root' user is able to login and the message 'Auto image Upgrade will start'
        appears
        """
        self._enter_juniper_config_mode(child=child)
        return True

    def enter_vm_console(self):
        child = pexpect.spawn(f'virsh console {self.vm_name} --force')
        child.expect('Escape character is')
        return child

    def wait_for_juniper_boot(self, timeout=60 * 15):
        """
        wait until juniper VM is fully booted
        """
        print(f"waiting for juniper vm '{self.vm_name}' to boot")
        local_path = os.path.join(self.JUNIPER_IMAGE['local_dir'], self.vm_name)
        child = pexpect.spawn(f"bash -c './vmx.sh --console vcp {self.vm_name}'", cwd=local_path)
        child.expect('to exit anytime')
        time_before = monotonic()
        time_end = time_before + timeout
        while monotonic() < time_end:
            try:
                if self._is_juniper_booted(child):
                    return child
            except pexpect.exceptions.ExceptionPexpect:
                pass
            sleep(1)
        print(f"ERROR: juniper vm '{self.vm_name}' failed to boot within '{timeout}' seconds")
        exit(1)

    def wait_for_cisco_boot(self, timeout=60 * 15):
        """
        wait until cisco VM is fully booted
        """
        print(f"waiting for cisco vm '{self.vm_name}' to boot")
        child = self.enter_vm_console()
        time_before = monotonic()
        time_end = time_before + timeout
        while monotonic() < time_end:
            try:
                if self._is_cisco_booted(child):
                    return True
            except pexpect.exceptions.ExceptionPexpect:
                pass
            sleep(1)
        print(f"ERROR: cisco vm '{self.vm_name}' failed to boot within '{timeout}' seconds")
        exit(1)

    def set_juniper_cpu_binding(self):
        """
        installation of juniper vm using the 'vmx.sh' script doesn't support binding specific CPUs to the vm,
        so this has to be done after the VM is already installed and running.
        """
        re_cpu = self.juniper_cpus[0]
        fe_cpus = self.juniper_cpus[1:]
        re_vm_name = f"vcp-{self.vm_name}"
        fe_vm_name = f"vfp-{self.vm_name}"
        print(f"binding cpu '{re_cpu}' to vm '{re_vm_name}'")
        send_host_cmd(f"virsh vcpupin {re_vm_name} --vcpu 0 {re_cpu} --config --live")
        print(f"binding cpus {fe_cpus} to vm '{fe_vm_name}'")
        for i, cpu in enumerate(fe_cpus):
            send_host_cmd(f"virsh vcpupin {fe_vm_name} --vcpu {i} {cpu} --config --live")

    def bind_juniper_dev_interfaces(self):
        """
        once the VM is installed, bridge interfaces must be bound to the VM using the vmx.sh script
        """
        local_path = os.path.join(self.JUNIPER_IMAGE['local_dir'], self.vm_name)
        print(f"binding bridges to juniper vm '{self.vm_name}'")
        send_host_cmd("./vmx.sh --bind-dev", cwd=local_path)

    def set_juniper_base_config(self, child, mgmt_ipv4_addr):
        """
        paste the basic CLI config, including hostname, SSH access, management IP and optional license.
        keep pasting configuration until it is applied.
        """
        print(f"setting basic configuration for juniper vm '{self.vm_name}'")
        retries = 7
        matches = 3
        for i in range(retries):
            try:
                if not matches:
                    return
                self._enter_juniper_config_mode(child=child)
                self._set_juniper_base_config(mgmt_ipv4_addr, child)
                child.sendline(f"show | display set | match {mgmt_ipv4_addr}")
                child.expect(mgmt_ipv4_addr)
                matches -= 1
                sleep(7)
            except pexpect.exceptions.ExceptionPexpect:
                if i == retries - 1:
                    raise

    def _install_juniper_license(self, child):
        if self.JUNIPER_IMAGE['license']:
            print(f"installing license to juniper vm '{self.vm_name}'")
            child.sendline("run request system license add terminal")
            child.expect("between each license key]")
            line_len = 100
            for line in self.JUNIPER_IMAGE['license']:
                splitted = [line[y-line_len:y] for y in range(line_len, len(line)+line_len,line_len)]
                for line_part in splitted:
                    child.send(line_part)
                child.sendline()
            child.sendcontrol('d')
            child.expect('successfully added')
            license_config = """set chassis license bandwidth 100
            set chassis license scale premium
            commit"""
            for line in license_config.splitlines():
                child.sendline(line)
            child.expect(f"commit complete", timeout=60 * 3)

    def _set_juniper_base_config(self, mgmt_ipv4_addr, child):
        xml_mgmt_ip = f"set interfaces fxp0 unit 0 family inet address {mgmt_ipv4_addr}" if self.mgmt_ip else ""
        xml_mgmt_gw = f"set routing-options static route 0.0.0.0/0 next-hop {self.mgmt_gw}" if self.mgmt_gw else ""
        base_config = f"""delete chassis
delete system
delete interfaces
set system host-name {self.vm_name}
set system login user dn class super-user
set system login user dn authentication encrypted-password "$1$scZ4w386$a8lkeMgTtA2kDhbLw2.F/0"
set system root-authentication encrypted-password "$1$ZU9q2yI7$w6mcJFeLW4zmltHke4jcq1"
set system services ssh
{xml_mgmt_ip}
{xml_mgmt_gw}
{self.cli_config}
commit
"""
        child.sendcontrol('d')
        for line in base_config.splitlines():
            child.sendline(line)
        child.expect(f"commit complete", timeout=60 * 3)

    def _enter_juniper_config_mode(self, child=None):
        """
        enter juniper 'config' mode using console connection
        """
        if not child:
            assert self.vm_name, "'vm_name' not provided to '_enter_juniper_config_mode'"
            local_path = os.path.join(self.JUNIPER_IMAGE['local_dir'], self.vm_name)
            child = pexpect.spawn(f"bash -c './vmx.sh --console vcp {self.vm_name}'", cwd=local_path)
        child.sendline('\n\r')
        child.expect(r"login:|root@:~ #|root.*>|edit.*#")
        if 'login:' in child.after.decode():
            child.sendline("root")
            child.expect("root@:~ #")
        if 'root@:~ #' in child.after.decode():
            child.sendline("cli")
            child.expect("root.*>", timeout=60 * 3)
        if 'root' in child.after.decode() and '>' in child.after.decode():
            child.sendline('configure')
            child.expect("edit.*#")
        return child

    def set_cisco_base_config(self, mgmt_ipv4_addr):
        """
        paste the basic CLI config, including hostname, SSH access and management IP
        """
        xml_if_ip = xml_mgmt_gw = ""
        if self.mgmt_ip:
            ip_interface = ipaddress.ip_interface(mgmt_ipv4_addr)
            ip = ip_interface.ip
            mask = ip_interface.netmask
            xml_if_ip = f"ipv4 address {ip} {mask}"

        if self.mgmt_gw:
            xml_mgmt_gw = f"""router static
 address-family ipv4 unicast
  0.0.0.0/0 {self.mgmt_gw}
 !
!"""

        base_config = f"""hostname {self.vm_name}
        username dn
         group root-lr
         group cisco-support
         secret 10 $6$FJabgZt79Sm0g...$UbEAn2FSiVMTnS9TTfgOa.XclZVVNpd1ZQ.649eGPwpeJW2G6AqO2GP.iLLWKyvqd7O7UxrRcq5Lyw7cf9C2B.
        !
         line console
         width 512
        !
        line default
         exec-timeout 0 0
         width 512
         length 0
         transport input ssh
        !
        vty-pool default 0 4 line-template default
        interface MgmtEth0/RP0/CPU0/0
         mtu 1500
         {xml_if_ip}
        !
        {xml_mgmt_gw}
        ssh server v2
        ssh server vrf default
        xml agent tty
         iteration off
        !
        {self.cli_config}
        """
        print(f"setting basic configuration for cisco vm {self.vm_name}")
        child = self.enter_vm_console()
        child.sendline('end')
        child.sendline('no')
        child.expect(r'.*')  # clear the buffer
        child.sendline('configure')
        child.expect(r'\(config.*\)')
        child.sendline(base_config + '\ncommit replace')
        child.expect(r'\[no\]:')
        child.sendline('yes')
        child.expect(r'yes.*\(config.*')
        child.sendline('end')


def get_or_create_bridges(count):
    """
    find empty bridges on the host. if not enough interfaces found, create new ones and enable them.
    """
    all_bridges = {br_name: bool(ifs) for br_name, ifs in get_bridges_info().items() if re.match(r'br\d+', br_name)}
    available_bridges = [br for br, has_ifs in all_bridges.items() if not has_ifs][:count]
    if len(available_bridges) == count:
        return available_bridges

    # find the highest configured bridge name and start counting from there
    br_numbers = [int(re.match(r'br(\d+)', br).group(1)) for br in all_bridges]
    highest_br = sorted(br_numbers)[-1]

    # create extra bridges
    missing_bridges = count - len(available_bridges)
    new_bridges_nums = list(range(highest_br + 1, highest_br + missing_bridges + 1))
    for br_num in new_bridges_nums:
        br_name = f"br{br_num}"
        available_bridges.append(br_name)
        print(f"creating bridge {br_name}")
        send_host_cmd(f"brctl addbr {br_name}")

    # enable all bridges
    for bridge in available_bridges:
        send_host_cmd(f"sudo ip l set {bridge} up")

    return available_bridges


def delete_vms(vm_name):
    """
    delete a vm, virsh config and storage lf all VMs will be removed.
    """
    vms_im_group = get_vm_names_by_group_id(vm_name)
    if not vms_im_group:
        exit(f"no VMs found in group '{vm_name}'")
    errors = []

    def _send_host_cmd(cmd, **kwargs):
        if send_host_cmd(cmd, strict=False, return_status_code=True, stderr=subprocess.PIPE, **kwargs) != 0:
            errors.append(f"failed to execute command '{cmd}'")

    for vm in vms_im_group:
        if 'vfp-' in vm:
            continue  # each juniper is actually 2 VMs, handle deletion on 'vcp-' iteration
        image_path = send_host_cmd(f"virsh dumpxml {vm} | grep 'source file' | grep {vm_name} | cut -d \\' -f2")
        if 'vcp-' in vm:  # if juniper
            dir_name = re.match(r'vcp-(.*)', vm).group(1)
            dir_path = re.match(r'(.*?%s)' % dir_name, image_path).group(1)
            _send_host_cmd("./vmx.sh --cleanup", cwd=dir_path)
            _send_host_cmd(f"rm -rf {dir_path}")
            continue
        # if cisco vm
        destroy_cmd = f"virsh destroy {vm}"
        undefine_cmd = f"virsh undefine {vm} --remove-all-storage --nvram"
        del_image_cmd = f"rm -rf {image_path}" if image_path else ''
        for cmd in (destroy_cmd, undefine_cmd, del_image_cmd):
            _send_host_cmd(cmd)
    if errors:
        print('\n'.join(errors))
    else:
        print(f"vm '{vm_name}' successfully deleted")


def get_vm_names_by_group_id(group_id):
    """
    get the names of all VMs in a group
    """
    return send_host_cmd("virsh list --all --name | grep %s" % group_id).splitlines()


def get_available_cpus():
    """
    find free dev-vm types(e.g re1, re2, etc) based on the host resources and the running VMs.

    - execute the 'create_vm.py' script with relevant parameters and parse the 'choose VM Type' part to determine
      the available dev-vm options and their CPU assignments (e.g re1-cpus 4 and 6, etc)
    - find the allocated CPUs of all running VMs using the 'virsh vcpuinfo' command
    - build a dictionary of free vm types as {type: [cpus]} ( e.g {re1: [4, 6]} )
    """
    # get allocated CPUs
    _used_cpus = send_host_cmd('virsh list --name | xargs -I {} virsh vcpuinfo {} | grep -E "^CPU:" | cut -d ":" -f2')
    used_cpus = [cpu.strip() for cpu in _used_cpus.splitlines()]
    total_cpus = int(send_host_cmd("cat /proc/cpuinfo | grep processor | wc -l").strip())
    return [cpu for cpu in range(1, total_cpus + 1) if str(cpu) not in used_cpus]


def install_prereqs_and_delete():
    """
    - validate that the script is running with required privileges and correct options
    - delete group if the --delete flag is set
    - install host requirements if the 'install_prereq' flag is set
    """
    if os.geteuid() != 0:
        exit("this script requires root privileges")
    if args.delete:
        delete_vms(args.name)
        exit(0)
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


def get_bridges_info():
    """
    get a dict of {bridge_name: [attached_interfaces]}
    """
    bridge_names = send_host_cmd("brctl show | awk 'NF>1 && NR>1 {print $1}'").splitlines()
    return {br_name: send_host_cmd(f"ls /sys/devices/virtual/net/{br_name}/brif/").splitlines()
            for br_name in bridge_names}


def save_br_and_net_config():
    """
    - save all bridges configuration to `netplan` in order for them to be persistent on next boot.
      all bridges on the host that starts with 'br' following a number will be saved. (br1, br2, br2, etc)
    - save mark all virsh-networks to auto-start on next boot
    """
    # mark virsh-networks to auto-start
    print("marking all virsh-networks as 'autostarted'")
    networks = send_host_cmd("virsh net-list --no-autostart --name").splitlines()
    for network in networks:
        send_host_cmd(f"virsh net-autostart {network}")

    # fetch the existing netplan config and parse it
    br_info = get_bridges_info()
    netplan_file_path = "/etc/netplan/01-netcfg.yaml"
    with open(netplan_file_path) as f:
        netplan_yaml = yaml.load(f)
    if not netplan_yaml:
        exit(f"ERROR: failed to fetch existing netplan config from {netplan_file_path}")

    # add new bridges configuration to netplan
    netplan_bridges = netplan_yaml['network']['bridges']
    for br_name, interfaces in br_info.items():
        if br_name in netplan_bridges or not re.match(r'br\d+', br_name):
            continue
        netplan_bridges[br_name] = {
            'dhcp4': False,
            'dhcp6': False
        }

    # override the netplan file with all the changes
    print(f"writing bridge and interfaces config to netplan at '{netplan_file_path}'")
    with open(netplan_file_path, 'w') as f:
        yaml.dump(netplan_yaml, f)


def get_avail_disk_space():
    return send_host_cmd("df -k | grep '/var/lib/libvirt/images' | awk '{print $4}'")


def name_type(arg_value):
    max_jun_name = 6
    if 'juniper' in sys.argv and len(arg_value) > max_jun_name:
        raise argparse.ArgumentTypeError(f"juniper VM name cannot exceed {max_jun_name} characters")
    return arg_value


def interface_type(arg_value):
    pat = re.compile(r"^(net|br):\w+$")
    if not pat.match(arg_value):
        raise argparse.ArgumentTypeError('each interface should follow the format of "type:value" e.g "br:br5"')
    return arg_value


def mgmt_ip_type(arg_value):
    pat = re.compile(r"^([\d.]+/\d+)$")
    match = pat.match(arg_value)
    if match:
        try:
            ipaddress.ip_interface(match.group(1))
            return arg_value
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(
        'mgmt ip should be in format <ip/pfx> e.g "e.g 10.0.0.1/20"')

def mgmt_gw_type(arg_value):
    pat = re.compile(r"^([\d.]+)$")
    match = pat.match(arg_value)
    if match:
        try:
            ipaddress.ip_interface(match.group(1))
            return arg_value
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(
        'mgmt gw should be a valid ipv4 address')


def get_required_disk_space(cisco_count, juniper_count):
    return (cisco_count * InteropEnv.CISCO_IMAGE['image_size_gb'] +
            juniper_count * InteropEnv.JUNIPER_IMAGE['image_size_gb'])


def get_required_ram_in_gb(cisco_count, juniper_count):
    return (cisco_count * (InteropEnv.CISCO_IMAGE['memory_kb'] / (1024 * 1024)) +
            juniper_count * ((InteropEnv.JUNIPER_IMAGE['vcp_memory_mb'] +
                              InteropEnv.JUNIPER_IMAGE['vfp_memory_mb']) / 1024))


def get_or_create_host_br(*host_ifs):
    """
    return the bridge that is attached to the host interface.
    if the host is already attached to a bridge, return that bridge
    """
    br_interfaces = []
    all_interfaces = send_host_cmd("brctl show | awk 'NF>1 && NR>1 {print $1 \" \" $4}'").splitlines()
    host_to_br_ifs = {}
    for line in all_interfaces:
        br_name, *_host_if = line.strip().split()
        host_if = _host_if[0] if _host_if else br_name
        host_to_br_ifs[host_if] = br_name

    # if the temporary bridge is used, make sure it exists
    tmp_br_name = 'brAutoTmp'
    if tmp_br_name in host_ifs and tmp_br_name not in host_to_br_ifs.values():
        send_host_cmd(f"brctl addbr {tmp_br_name}")
        host_to_br_ifs[tmp_br_name] = tmp_br_name

    for interface in host_ifs:
        if interface in host_to_br_ifs:  # if a physical host interface provided
            br_interfaces.append(host_to_br_ifs[interface])
        elif interface in host_to_br_ifs.values():  # if a bridge was provided
            br_interfaces.append(interface)
        else:
            new_br = get_or_create_bridges(1)[0]
            print(f"attaching interface '{interface}' to bridge '{new_br}'")
            br_interfaces.append(new_br)  # create a new bridge and attach the host interface to it
            send_host_cmd(f"brctl addif {new_br} {interface}").splitlines()
    return br_interfaces


# noinspection PyTypeChecker
parser = argparse.ArgumentParser(
    formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=50, width=150),
    description="""create or delete a single Cisco or Juniper VM, with optional management-ip configuration(fxp0) and interface-binding
for example, a Cisco VM with mgmt-ip, 2 bridge interfaces, 'br1' and 'br2', and an internal virsh-network 'someNetwork', can be created using the below command:
sudo ./create_single_vm.py --name my_cisco --type cisco --mgmt_ip 10.0.0.1/20 --mgmt_gw 10.0.15.254 --interfaces br:br1 br:br2 net:someNetwork""")
parser.add_argument("--mgmt_br", type=str, default="br0", help="management bridge of the host (default: br0)")
parser.add_argument("--mgmt_ip", type=mgmt_ip_type, help="VM management interface to enable SSH after the VM is installed")
parser.add_argument("--mgmt_gw", type=mgmt_gw_type, help="default gateway for the management network")
parser.add_argument("--config", type=str, help="path to a local config file to paste into the device")
parser.add_argument("--delete", action="store_true", help="delete all vms that includes the provided name. will undefine "
                                                          "vms and delete images (default: False)")
parser.add_argument("--check", action="store_true",
                    help="check if your selections are valid and if there are enough resources to configure the "
                         "requested groups. this will display the allocated resources or an error message. no new VMs "
                         "will be created. (default: False)")
parser.add_argument("--dont_save_br_config", action="store_true",
                    help="don't save bridge configuration to netplan. this should be used only when creating temporary "
                         "VMs that don't need to survive host reboot (default: False)")
parser.add_argument("--install_prereq", action="store_true",
                    help="install required packages on the host. should only run once per host (default: False)")
parser.add_argument("--name", type=name_type, help="name of the router VM", required=True)
parser.add_argument("--type", type=str, help="router type, either cisco v7.0.2 or juniper v20.4R1.12", choices=['cisco', 'juniper'], default='cisco')
parser.add_argument("--interfaces", type=interface_type, nargs='+',
                    help="interfaces to attach from the host to VM. in format of `type:value`. where 'type' can be either 'net' or 'br'. e.g net:someNetwork br:br5")


def validate_cpus(cisco_count, juniper_count, available_cpus=None):
    required_cpus = 2 * cisco_count + 4 * juniper_count
    if not available_cpus:
        available_cpus = get_available_cpus()
    if required_cpus > len(available_cpus):
        exit("not enough available CPUs found for VM installation")
    return available_cpus[:required_cpus]


def print_requirements(cisco_count, juniper_count, name, type):
    required_disk_space_gb = get_required_ram_in_gb(cisco_count, juniper_count)
    required_ram_gb = get_required_ram_in_gb(cisco_count, juniper_count)
    free_cpus = validate_cpus(cisco_count, juniper_count)
    print(f"name: {name}\n"
          f"type: {type}\n"
          f"cpus: {','.join([str(cpu) for cpu in free_cpus])}\n"
          f"disk-space: {int(required_disk_space_gb)}G\n"
          f"memory: {int(required_ram_gb)}G")


if __name__ == '__main__':
    args = parser.parse_args()
    before = monotonic()
    # check user selections, fetch the needed info and handle prereq and deletion operations
    install_prereqs_and_delete()

    # validate resources
    cisco_count = 1 if args.type == 'cisco' else 0
    juniper_count = 1 if args.type == 'juniper' else 0

    # prepare all the info needed to start the installation
    if args.check:
        print_requirements(cisco_count, juniper_count, args.name, args.type)
        exit(0)
    free_cpus = validate_cpus(cisco_count, juniper_count)
    cli_config = None
    if args.config:
        with open(args.config) as f:
            cli_config = f.read()
    InteropEnv(args.mgmt_br, free_cpus, args.name, args.type, args.interfaces, args.mgmt_ip, args.mgmt_gw, cli_config)()

    # make the bridges and virsh-network configuration persistent
    if not args.dont_save_br_config:
        save_br_and_net_config()
    print(f"script done in '{monotonic() - before}' seconds")

