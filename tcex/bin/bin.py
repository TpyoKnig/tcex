#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TcEx Framework Bin Command Base Module."""
import json
import os
import sys

import colorama as c
import redis

from ..app_config_object import InstallJson, LayoutJson, TcexJson
from ..app_config_object.permutations import Permutations


class Bin:
    """Base Class for ThreatConnect command line tools.

    Args:
        _args (namespace): The argparser args Namespace.
    """

    def __init__(self, _args):
        """Initialize Class properties.

        Args:
            _args (namespace): The argparser args Namespace.
        """
        self.args = _args

        # properties
        self._redis = None
        self._tcex_json = None
        self.app_path = os.getcwd()
        self.exit_code = 0
        self.ij = InstallJson()
        self.lj = LayoutJson()
        self.permutations = Permutations()
        self.tj = TcexJson()

        # initialize colorama
        c.init(autoreset=True, strip=False)

    @staticmethod
    def handle_error(err, halt=True):
        """Print errors message and optionally exit.

        Args:
            err (str): The error message to print.
            halt (bool, optional): Defaults to True. If True the script will exit.
        """
        print(f'{c.Style.BRIGHT}{c.Fore.RED}{err}')
        if halt:
            sys.exit(1)

    @staticmethod
    def print_message(message, line_bright=False, line_color=None, line_limit=100):
        """Print the message ensuring lines don't exceed line limit."""
        bright = ''
        if line_bright:
            bright = c.Style.BRIGHT
        message_line = ''
        for word in message.split(' '):
            if len(message_line) + len(word) < line_limit:
                message_line += f'{word} '
            else:
                print(f'{bright}{line_color}{message_line.rstrip()}')
                message_line = f'{word} '
        print(f'{bright}{line_color}{message_line.rstrip()}')

    def profile_settings_args_layout_json(self, required):
        """Return args based on layout.json and conditional rendering.

        Args:
            required (bool): If True only required args will be returned.

        Returns:
            dict: Dictionary of required or optional App args.
        """
        profile_args = {}
        try:
            for pn in self.permutations.input_permutations[self.args.permutation_id]:
                p = self.ij.filter_params_dict(required=required).get(pn.get('name'))
                if p is None:
                    continue

                if p.get('type').lower() == 'boolean':
                    # use the value generated in the permutation
                    profile_args[p.get('name')] = pn.get('value')
                elif p.get('type').lower() == 'choice':
                    # use the value generated in the permutation
                    profile_args[p.get('name')] = pn.get('value')
                elif p.get('type').lower() == 'keyvaluelist':
                    profile_args[p.get('name')] = '<KeyValueList>'
                elif p.get('name') in ['api_access_id', 'api_secret_key']:
                    # leave these parameters set to the value defined in defaults
                    pass
                else:
                    # add type stub for values
                    types = '|'.join(p.get('playbookDataType', []))
                    if types:
                        profile_args[p.get('name')] = p.get('default', f'<{types}>')
                    else:
                        profile_args[p.get('name')] = p.get('default', '')
        except IndexError:
            self.handle_error('Invalid permutation index provided.')
        return profile_args

    @property
    def redis(self):
        """Return instance of Redis."""
        if self._redis is None:
            self._redis = redis.StrictRedis(host=self.args.redis_host, port=self.args.redis_port)
        return self._redis

    @property
    def tcex_json(self):
        """Return tcex.json file contents."""
        file_fqpn = os.path.join(self.app_path, 'tcex.json')
        if self._tcex_json is None:
            if os.path.isfile(file_fqpn):
                try:
                    with open(file_fqpn, 'r') as fh:
                        self._tcex_json = json.load(fh)
                except ValueError as e:
                    self.handle_error(f'Failed to load "{file_fqpn}" file ({e}).')
            else:
                # self.handle_error(f'File "{file_fqpn}" could not be found.')
                self._tcex_json = {}
        return self._tcex_json

    @staticmethod
    def update_system_path():
        """Update the system path to ensure project modules and dependencies can be found."""
        cwd = os.getcwd()
        lib_dir = os.path.join(os.getcwd(), 'lib_')
        lib_latest = os.path.join(os.getcwd(), 'lib_latest')

        # insert the lib_latest directory into the system Path if no other lib directory found. This
        # entry will be bumped to index 1 after adding the current working directory.
        if not [p for p in sys.path if lib_dir in p]:
            sys.path.insert(0, lib_latest)

        # insert the current working directory into the system Path for the App, ensuring that it is
        # always the first entry in the list.
        try:
            sys.path.remove(cwd)
        except ValueError:
            pass
        sys.path.insert(0, cwd)
