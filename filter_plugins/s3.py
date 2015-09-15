# -*- coding: utf-8 -*-
# (c) 2015, Taneli Leppä <rosmo@rosmo.fi>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#
# Based of ipaddr.py filter

from functools import partial
import os

try:
    from boto.s3.connection import S3Connection
    import boto
except ImportError:
    # in this case, we'll make the filters return error messages (see bottom)
    S3Connection = None

from ansible import errors

def _need_boto(f_name, *args, **kwargs):
    raise errors.AnsibleFilterError('The {0} filter requires Boto to be'
            ' installed on the ansible controller'.format(f_name))

def get_signed_s3_url(value, host=None, bucket=None, aws_access_key=None, aws_secret_key=None, https=True, expiry=631138519, method='GET'):
    if not boto.config.get('s3', 'use-sigv4'):
        boto.config.add_section('s3')
        boto.config.set('s3', 'use-sigv4', 'True')
    if not aws_access_key:
        if 'EC2_ACCESS_KEY' in os.environ:
            aws_access_key = os.environ['EC2_ACCESS_KEY']
        elif 'AWS_ACCESS_KEY_ID' in os.environ:
            aws_access_key = os.environ['AWS_ACCESS_KEY_ID']
        elif 'AWS_ACCESS_KEY' in os.environ:
            aws_access_key = os.environ['AWS_ACCESS_KEY']

    if not aws_secret_key:
        if 'EC2_SECRET_KEY' in os.environ:
            aws_secret_key = os.environ['EC2_SECRET_KEY']
        elif 'AWS_SECRET_ACCESS_KEY' in os.environ:
            aws_secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
        elif 'AWS_SECRET_KEY' in os.environ:
            aws_secret_key = os.environ['AWS_SECRET_KEY']

    c = boto.connect_s3(aws_access_key, aws_secret_key, host=host)
    #    c = S3Connection(aws_access_key, aws_secret_key, host=host)
    return c.generate_url(
        expires_in=long(expiry),
        method=method,
        bucket=bucket,
        key=value,
        force_http=(not https)
    )

class FilterModule(object):
    ''' Generate signed S3 URLs '''
    filter_map =  {
        'get_signed_s3_url': get_signed_s3_url
    }

    def filters(self):
        if S3Connection:
            return self.filter_map
        else:
            # Need to install python-netaddr for these filters to work
            return dict((f, partial(_need_boto, f)) for f in self.filter_map)
