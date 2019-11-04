# Copyright (c) 2018 Orange.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging

from osc_lib.cli import format_columns
from osc_lib.cli.parseractions import KeyValueAction
from osc_lib.command import command
from osc_lib import exceptions
from osc_lib import utils as osc_utils
from osc_lib.utils import columns as column_util

from neutronclient._i18n import _
from neutronclient.osc import utils as nc_osc_utils

LOG = logging.getLogger(__name__)

INTERCONNECTION = 'interconnection'
INTERCONNECTIONS = 'interconnections'

_attr_map = (
    ('id', 'ID', column_util.LIST_BOTH),
    ('project_id', 'Project', column_util.LIST_LONG_ONLY),
    ('name', 'Name', column_util.LIST_BOTH),
    ('type', 'Type', column_util.LIST_BOTH),
    ('state', 'State', column_util.LIST_BOTH),
    ('local_resource_id', 'Local Neutron Resource',
     column_util.LIST_LONG_ONLY),
    ('remote_resource_id', 'Remote Neutron Resource',
     column_util.LIST_LONG_ONLY),
    ('remote_keystone', 'Remote Keystone URL', column_util.LIST_LONG_ONLY),
    ('remote_region', 'Remote Region', column_util.LIST_LONG_ONLY),
    ('remote_interconnection_id', 'Remote Interconnection',
     column_util.LIST_LONG_ONLY),
    ('local_parameters', 'Local Parameters', column_util.LIST_LONG_ONLY),
    ('remote_parameters', 'Remote Parameters', column_util.LIST_LONG_ONLY),
)


class CreateInterconnection(command.ShowOne):
    _description = _("Create an interconnection for a given project")

    def get_parser(self, prog_name):
        parser = super(CreateInterconnection, self).get_parser(prog_name)
        parser.add_argument(
            'name',
            metavar='<name>',
            help=_("Name of the interconnection to create")
        )
        parser.add_argument(
            '--type',
            default='network_l3',
            choices=['router', 'network_l2', 'network_l3'],
            help=_("Interconnection type selection between router, l2 and l3 "
                   "network (default: network_l3)")
        )
        parser.add_argument(
            '--local-resource',
            metavar='<local-resource>',
            required=True,
            help=_('Local neutron resource (name or ID)')
        )
        parser.add_argument(
            '--remote-resource',
            metavar='<remote-resource>',
            required=True,
            help=_('Remote neutron resource (name or ID)')
        )
        parser.add_argument(
            '--remote-keystone',
            metavar='<remote-keystone>',
            required=True,
            help=_('Remote keystone URL')
        )
        parser.add_argument(
            '--remote-region',
            metavar='<remote-region>',
            required=True,
            help=_('Remote region')
        )

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        attrs = _get_common_attrs(parsed_args)
        body = {INTERCONNECTION: attrs}
        obj = client.create_interconnection(body)[INTERCONNECTION]
        columns, display_columns = column_util.get_columns(obj, _attr_map)
        data = osc_utils.get_dict_properties(obj, columns)
        return display_columns, data


class DeleteInterconnection(command.Command):
    _description = _("Delete a given interconnection")

    def get_parser(self, prog_name):
        parser = super(DeleteInterconnection, self).get_parser(prog_name)
        parser.add_argument(
            'interconnections',
            metavar="<interconnection>",
            nargs="+",
            help=_("Interconnection(s) to delete (name or ID)")
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        fails = 0
        for id_or_name in parsed_args.interconnections:
            try:
                id = client.find_resource(INTERCONNECTION, id_or_name)['id']
                client.delete_interconnection(id)
                LOG.warning("Interconnection %(id)s deleted", {'id': id})
            except Exception as e:
                fails += 1
                LOG.error("Failed to delete interconnection with name or ID "
                          "'%(id_or_name)s': %(e)s",
                          {'id_or_name': id_or_name, 'e': e})
        if fails > 0:
            msg = (_("Failed to delete %(fails)s of %(total)s "
                     "interconnection.") %
                   {'fails': fails,
                    'total': len(parsed_args.interconnections)})
            raise exceptions.CommandError(msg)


class ListInterconnection(command.Lister):
    _description = _("List interconnections")

    def get_parser(self, prog_name):
        parser = super(ListInterconnection, self).get_parser(prog_name)
        parser.add_argument(
            '--long',
            action='store_true',
            default=False,
            help=_("List additional fields in output")
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        data = client.list_interconnections()
        headers, columns = column_util.get_column_definitions(
            _attr_map, long_listing=parsed_args.long)
        return (headers,
                (osc_utils.get_dict_properties(s, columns)
                 for s in data['interconnections']))


class SetInterconnection(command.Command):
    _description = _("Set interconnection properties")

    def get_parser(self, prog_name):
        parser = super(SetInterconnection, self).get_parser(prog_name)
        parser.add_argument(
            '--name',
            metavar='<name>',
            help=_('Name of the interconnection'))
        parser.add_argument(
            'interconnection',
            metavar='<interconnection>',
            help=_("Interconnection to modify (name or ID)")
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        id = client.find_resource(INTERCONNECTION,
                                  parsed_args.interconnection)['id']
        attrs = _get_common_attrs(parsed_args, is_create=False)
        body = {INTERCONNECTION: attrs}
        try:
            client.update_interconnection(id, body)
        except Exception as e:
            msg = (_("Failed to update interconnection '%(interconnection)s': "
                     "%(e)s")
                   % {'interconnection': parsed_args.interconnection, 'e': e})
            raise exceptions.CommandError(msg)


class ShowInterconnection(command.ShowOne):
    _description = _("Show information of a given interconnection")

    def get_parser(self, prog_name):
        parser = super(ShowInterconnection, self).get_parser(prog_name)
        parser.add_argument(
            'interconnection',
            metavar="<interconnection>",
            help=_("Interconnection to display (name or ID)"),
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        id = client.find_resource(INTERCONNECTION,
                                  parsed_args.interconnection)['id']
        obj = client.show_interconnection(id)[INTERCONNECTION]
        columns, display_columns = column_util.get_columns(obj, _attr_map)
        data = osc_utils.get_dict_properties(obj, columns)
        return display_columns, data


def _get_common_attrs(parsed_args, is_create=True):
    attrs = {}
    if parsed_args.name is not None:
        attrs['name'] = parsed_args.name
    if is_create:
        _get_attrs(attrs, parsed_args)
    return attrs


def _get_attrs(attrs, parsed_args):
    if parsed_args.type is not None:
        attrs['type'] = parsed_args.type
    if parsed_args.local_resource is not None:
        attrs['local_resource_id'] = parsed_args.local_resource
    if parsed_args.remote_resource is not None:
        attrs['remote_resource_id'] = parsed_args.remote_resource
    if parsed_args.remote_keystone is not None:
        attrs['remote_keystone'] = parsed_args.remote_keystone
    if parsed_args.remote_region is not None:
        attrs['remote_region'] = parsed_args.remote_region
