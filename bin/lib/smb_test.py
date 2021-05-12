import socket
from smb.SMBConnection import SMBConnection
import traceback
import re

domain = 'home'
username = 'jrmurray'
password = 'Th1nkb4#app'
server_name = '192.168.2.62'

# Get the local client hostname
client_name = socket.gethostname()
# Delete any domain from the client hostname string
if '.' in client_name:
    client_name = client_name[0:client_name.index('.')]

try:
    conn = SMBConnection(username, password, client_name, server_name, domain=domain, use_ntlm_v2=True,
                         sign_options = SMBConnection.SIGN_WHEN_SUPPORTED) 
    connected = conn.connect(server_name, 139)

    try:
        Response = conn.listShares(timeout=30)  # obtain a list of shares
        print('Shares on: ' + server_name)
        for i in range(len(Response)):  # iterate through the list of shares
            print("  Share[",i,"] =", Response[i].name)

            try:
                # list the files on each share
                if Response[i].name not in ['IPC$', 'ADMIN$']:
                    print("Files on: %s/  Share[%s] = %s" % (server_name, i, Response[i].name))
                    Response2 = conn.listPath(Response[i].name,'/',timeout=30)
                    for i in range(len(Response2)):
                        print("    File[",i,"] =", Response2[i].filename)
            except BaseException as e:
                print('Can not access the resource: ' + repr(e))
                #traceback.print_exc()
    except BaseException as e:
        print('Can not list shares: ' + repr(e))
        traceback.print_exc()

    try:
        target_config = {"share_name": "C$"}
        folder = '/temp/test1/test2/test3/'
        subfolders = ['/'] + folder.strip('/').split('/')
        if '' in subfolders:
            subfolders.remove('')
        print("Folders list for dir creation: %s" % str(subfolders))
        current_folder = ''
        folder_depth = len(subfolders) - 1
        for i, subfolder_name in enumerate(subfolders):
            current_folder = (current_folder + '/' + subfolder_name).replace('//', '/')
            print("Current folder = " + current_folder)
            try:
                conn.getAttributes(target_config['share_name'], current_folder, timeout=10)
            except:
                conn.createDirectory(target_config['share_name'], current_folder, timeout=10)



        with open('/Users/jrmurray/rmate', 'rb', buffering=0) as local_file:
            conn.storeFile('C$', '/temp/rmate', local_file)
            remote_dir = conn.getAttributes('C$', '/temp/rmate', timeout=30)
            print(remote_dir.isDirectory)
            print(remote_dir.isReadOnly)

    except BaseException as e:
        print('Can not upload the file: ' + repr(e))
        traceback.print_exc()

except BaseException as e:
    print('Can not access the system: ' + repr(e))
    traceback.print_exc()

