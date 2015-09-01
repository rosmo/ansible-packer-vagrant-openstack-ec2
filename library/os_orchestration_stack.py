#!/usr/bin/python
#
# Copyright (c) 2015, Taneli Leppa <rosmo@rosmo.fi>
# Based on os_keypair module
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
try:
    from keystoneclient.v2_0 import client as ksclient
    from heatclient import client as client
    from heatclient.v1.stacks import StackManager
    import yaml
    import json
    HAVE_DEPS = True
except ImportError, e:
    HAVE_DEPS = False

DOCUMENTATION = '''
---
module: os_orchestration_stack
short_description: Manage Heat stacks on OpenStack
extends_documentation_fragment: openstack
version_added: "2.0"
description:
  - Manage Heat stacks on Openstack
options:
  name:
    description:
      - Name for the Heat stack
    required: true
    default: None
  template:
    description:
      - Contents of the Heat template
    required: false
    default: None
  parameters:
    description:
      - Dictionary containing parameters for the Heat template.
    required: false
    default: None
  tags:
    description:
      - String containing comma separated tags for the Heat template.
    required: false
    default: None
  wait:
    description:
      - Wait for the stack creation to be complete.
    required: false
    default: True
  timeout:
    description:
      - Amount of time to wait for the stack creation to complete.
    required: false
    default: 120
  state:
    description:
      - Should the resource be present or absent.
    choices: [present, absent]
    default: present
requirements: []
'''

EXAMPLES = '''
  os_orchestration_stack:
     name: "teststack"
     template: "{{ lookup('template', '../templates/sample.yml.j2') }}"
     state: present
     parameters:
       key_name: "my-key"
       flavor: "tiny"
       image: "my-image-name"
       availability_zone: "zone-1"
  connection: local
'''

RETURN = '''
info:
    description: Heat stack contents.
    returned: success
    type: dict
'''

_os_keystone = None
_os_tenant_id = None

# Shade does not support Heat yet
def _get_ksclient(module, kwargs):
    try:
        kclient = ksclient.Client(username=kwargs['login_username'],
                                  password=kwargs['login_password'],
                                  tenant_name=kwargs['login_tenant_name'],
                                  auth_url=kwargs['auth_url'])
    except Exception, e:
        module.fail_json(msg = "Error authenticating to the keystone: %s" %e.message)
    global _os_keystone
    _os_keystone = kclient
    return kclient


def _set_tenant_id(module):
    global _os_tenant_id
    if 'login_tenant_id' in module.params and module.params['login_tenant_id']:
        _os_tenant_id = module.params['login_tenant_id']
        return
    
    tenant_name = module.params['login_tenant_name']

    _os_tenant_id = os.environ.get('OS_TENANT_ID', None)        
    if _os_tenant_id != None:
        return _os_tenant_id
    
    for tenant in _os_keystone.tenants.list():
        if tenant.name == tenant_name:
            _os_tenant_id = tenant.id
            break

    if not _os_tenant_id:
        module.fail_json(msg = "The tenant id cannot be found, please check the parameters")
        
def _get_endpoint(module, client, endpoint_type='publicURL'):
    try:
        endpoint = client.service_catalog.url_for(service_type='orchestration', endpoint_type=endpoint_type)
    except Exception, e:
        module.fail_json(msg="Error getting endpoint for glance: %s" % e.message)
    return endpoint

def _get_heat_client(module, kwargs):
    try:
        _ksclient = _get_ksclient(module, kwargs)
        token = _ksclient.auth_token
        endpoint = _get_endpoint(module, _ksclient)
        heat = client.Client('1', endpoint=endpoint, token=token)
    except Exception, e:
        module.fail_json(msg = "Error in connecting to heat: %s" % e.message)
        return heat
    return heat

def _json_helper(obj):
    import calendar, datetime

    if isinstance(obj, datetime.date):
        return obj.isoformat()

def main():
    argument_spec = openstack_argument_spec()
    argument_spec.update(dict(
        login_tenant_id = dict(required=False),
        name = dict(required=True),
        template = dict(required=False, no_log=True),
        parameters = dict(required=False, type='dict'),
        tags = dict(required=False, type='str'),
        wait = dict(required=False, default=True, type='bool'),
        timeout = dict(required=False, default=120, type='int'),
        state = dict(default='present', choices=['absent', 'present'])
    ))

    module = AnsibleModule(argument_spec)

    if not HAVE_DEPS:
        module.fail_json(msg='heatclient, yaml and json is required for this module')

    try:
        heat = _get_heat_client(module, module.params)
        _set_tenant_id(module)

        found_stack = None
        stacks = heat.stacks.list()
        for stack in stacks:
            if stack.stack_name.lower() == module.params['name'].lower():
                found_stack = stack
                break
            
        if 'template' in module.params:
            template = yaml.load(module.params['template'])
            template_json = json.dumps(template, default=_json_helper)

        parameters = module.params['parameters'] if 'parameters' in module.params else None;
        tags = module.params['tags'] if 'tags' in module.params else None;
            
        if module.params['state'] == 'present' and found_stack == None:
            _stack = heat.stacks.create(tenant_id=_os_tenant_id,
                                        stack_name=module.params['name'],
                                        template=module.params['template'],
                                        parameters=parameters,
                                        tags=tags)
            found_stack = heat.stacks.get(_stack['stack']['id'])
            expire = time.time() + int(module.params['timeout'])
            _stack_dict = found_stack.to_dict()
            while time.time() < expire:
                if _stack_dict['stack_status'] != 'CREATE_IN_PROGRESS':
                    break

                time.sleep(2)
                found_stack = heat.stacks.get(_stack['stack']['id'])
                _stack_dict = found_stack.to_dict()
            module.exit_json(changed=True, info=_stack_dict)
            
        if module.params['state'] == 'present' and found_stack != None:
            
            found_stack.get()
            _stack_dict = found_stack.to_dict()
            
            stack_template = json.dumps(heat.stacks.template(found_stack.identifier))
            changed = False
            if stack_template != template_json:
                changed = True
                
            if changed:
                _stack = heat.stacks.update(found_stack.identifier,
                                            tenant_id=_os_tenant_id,
                                            stack_name=module.params['name'],
                                            template=module.params['template'],
                                            parameters=parameters,
                                            tags=tags)
                found_stack = heat.stacks.get(found_stack.identifier)
                
                _stack_dict = found_stack.to_dict()
                expire = time.time() + int(module.params['timeout'])
                while time.time() < expire:
                    if _stack_dict['stack_status'] != 'UPDATE_IN_PROGRESS':
                        break

                    time.sleep(2)
                    found_stack = heat.stacks.get(found_stack.identifier)
                    _stack_dict = found_stack.to_dict()

                module.exit_json(changed=changed, info=_stack_dict)
            module.exit_json(changed=changed, info=_stack_dict)

        if module.params['state'] != 'present' and found_stack != None:
            heat.stacks.delete(found_stack.identifier)
            module.exit_json(changed=True)

        module.exit_json(changed=False)
            
    except Exception, e:
        module.fail_json(msg = "Heat error: %s" % e.message)

# this is magic, see lib/ansible/module_common.py
from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
if __name__ == '__main__':
    main()
