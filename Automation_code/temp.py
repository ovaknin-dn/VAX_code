import time
import concurrent.futures
from netmiko import ConnectHandler

hosts_info = []
with open('routers.txt', 'r') as devices:
    for line in devices:
        deviceip = line.strip()
        host = {
            'device_type': 'cisco_ios',
            'ip': deviceip,
            'username': 'iadmin',
            'password': 'iadmin',
            'secret': 'iadmin'
        }
        hosts_info.append(host)

starting_time = time.perf_counter()

def open_connection(host):
    try:
        connection = ConnectHandler(**host)

        print('Trying router', host['ip'])
        print('Connection Established to Host:', host['ip'])
        connection.enable()
        sendcommand = connection.send_command('show config | no-more')
        return sendcommand
    except:
        print('Connection Failed to host', host['ip'])


with concurrent.futures.ProcessPoolExecutor() as executor:
    results = executor.map(open_connection, hosts_info)

    for result in results:
        print(result)

finish = time.perf_counter()
print('Time Elapsed:', finish - starting_time)