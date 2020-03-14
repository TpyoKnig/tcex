#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TcEx App Init."""
import json
import os

import colorama as c

from .bin import Bin
from ..app_config_object.templates import DownloadTemplates


class Init(Bin):
    """Install required modules for ThreatConnect Job or Playbook App.

    Args:
        _args (namespace): The argparser args Namespace.
    """

    def __init__(self, _args):
        """Initialize Class properties.

        Args:
            _args (namespace): The argparser args Namespace.
        """
        super().__init__(_args)
        self.download_template = DownloadTemplates(self.args.branch)

    def update_tcex_json(self):
        """Update the tcex.json configuration file if exists."""
        if not os.path.isfile('tcex.json'):
            return

        # display warning on missing app_name field
        if self.tcex_json.get('package', {}).get('app_name') is None:
            print(f'{c.Fore.MAGENTA}The tcex.json file is missing the "app_name" field.')

        # display warning on missing app_version field
        if self.tcex_json.get('package', {}).get('app_version') is None:
            print(f'{c.Fore.YELLOW}The tcex.json file is missing the "app_version" field.')

        # update excludes
        excludes = [
            '.gitignore',
            '.pre-commit-config.yaml',
            'pyproject.toml',
            'setup.cfg',
            'tcex.json',
            '*.install.json',
            'tcex.d',
        ]

        if 'requirements.txt' in self.tcex_json.get('package').get('excludes', []):
            message = (
                f'{c.Fore.YELLOW}The tcex.json file excludes "requirements.txt". '
                f'This file is required to be App Builder compliant. Remove entry ([y]/n)? '
            )
            response = input(message) or 'y'
            if response in ['y', 'yes']:
                self.tcex_json.get('package', {}).get('excludes', []).remove('requirements.txt')

                with open('tcex.json', 'w') as f:
                    json.dump(self.tcex_json, f, indent=2, sort_keys=True)

        missing_exclude = False
        for exclude in excludes:
            if exclude not in self.tcex_json.get('package', {}).get('excludes', []):
                missing_exclude = True
                break

        if missing_exclude:
            message = (
                f'{c.Fore.YELLOW}The tcex.json file is missing excludes items. Update ([y]/n)? '
            )
            response = input(message) or 'y'

            if response in ['y', 'yes']:
                # get unique list of excludes
                excludes.extend(self.tcex_json.get('package', {}).get('excludes'))
                self.tcex_json['package']['excludes'] = sorted(list(set(excludes)))

                with open('tcex.json', 'w') as f:
                    json.dump(self.tcex_json, f, indent=2, sort_keys=True)
