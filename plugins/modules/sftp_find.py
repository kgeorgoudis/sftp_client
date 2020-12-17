#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020, Konstantinos Georgoudis <kgeorgoudis@icloud.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r'''
---
module: sftp_find

short_description: sftp find module

version_added: "1.0.0"

description:
    - Return a list of files based on specific criteria on an sftp host

options:
    path:
        description:
            - The path on the remote sftp host where the files are
            - It can be full path, relative path, or a . for current path
        required: true
        type: path
    pattern:
        description:
            - You can choose a filename, or wildcard ending with file extension
            - E.g. filename.txt or *.csv or ADD_????????_export.csv
        required: true
        type: str
    host:
        description:
            - The IP address or the FQDN of the remote sftp host
        required: true
        type: str
    port:
        description:
            - The TCP port of the remote sftp host. The default port is 22
        type: int
        default: 22
    username:
        description:
            - Username for the sftp connection
        required: true
        type: str
    method:
        description:
            - Choose authentication method between "password" or "private_key"
        choices: [ 'password', 'private_key' ]
        type: str
        required: true
    password:
        description:
            - Password for the sftp connection
        type: str
    private_key_path:
        description:
            - Private key for the sftp connection
        required: false
        type: path
    private_key_type:
        description:
            - Private key type "DSA" or "RSA"
        choices: [ 'DSA', 'RSA' ]
        type: str
        required: false

requirements:
- paramiko

author:
    - Konstantinos Georgoudis (@kgeorgoudis)
'''

EXAMPLES = r'''

- name: Find all csv files on the remote sftp host
  kgeor.sftp_modules.sftp_find:
    path: "/some_path"
    pattern: "*.csv"
    host: "test.example.com"
    port: 22
    username: "demo"
    password: "somepassword"
    method: "password"
  delegate_to: localhost

'''

import os
import fnmatch
import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.basic import missing_required_lib

LIB_IMP_ERR = None
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    LIB_IMP_ERR = traceback.format_exc()


def sftp_password_session(module, host, port, username, password):
    try:
        transport = paramiko.Transport(host, port)
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
    except Exception as e:
        module.fail_json(msg="Failed to connect on remote sftp host: %s" % e)
        if sftp is not None:
            sftp.close()
        if transport is not None:
            transport.close()
        pass

    return sftp


def sftp_key_session(module, host, username, port, private_key_path, private_key_type):
    try:
        transport = paramiko.Transport(host, port)
        if private_key_type == "DSA":
            key = paramiko.DSSKey.from_private_key_file(private_key_path)
        else:
            key = paramiko.RSAKey.from_private_key(private_key_path)
        transport.connect(username=username, pkey=key)
        sftp = paramiko.SFTPClient.from_transport(transport)
    except Exception as e:
        module.fail_json(msg="Failed to connect on remote sftp host: %s" % e)
        if sftp is not None:
            sftp.close()
        if transport is not None:
            transport.close()
        pass

    return sftp


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type='path', required=True),
            pattern=dict(type='str', required=True),
            host=dict(type='str', required=True),
            port=dict(type='int', default=22),
            username=dict(type='str', required=True),
            method=dict(type='str', choices=['password', 'private_key'], required=True),
            password=dict(type='str', no_log=True, required=False),
            private_key_path=dict(type='path', required=False),
            private_key_type=dict(type='str', required=False, choices=['DSA', 'RSA']),
        ),
        supports_check_mode=True,
        required_if=[
            ['method', 'password', ['password']],
            ['method', 'private_key', ['private_key_path', 'private_key_type']],
        ],
    )

    params = module.params

    looked = 0
    filelist = []

    path = params['path']
    pattern = params['pattern']
    host = params['host']
    port = params['port']
    username = params['username']
    password = params['password']
    method = params['method']
    private_key_path = params['private_key_path']
    private_key_type = params['private_key_type']

    if not PARAMIKO_AVAILABLE:
        module.fail_json(msg=missing_required_lib("paramiko"), exception=LIB_IMP_ERR)

    if method == "password":
        sftp = sftp_password_session(module, host, port, username, password)
    else:
        sftp = sftp_key_session(module, host, username, port, private_key_path, private_key_type)

    for file in sftp.listdir(path):
        looked += 1
        if fnmatch.fnmatch(file, pattern):
            full_name = os.path.join(path, file)
            filelist.append(full_name)

    module.exit_json(files=filelist, changed=False, examined=looked)


if __name__ == '__main__':
    main()
