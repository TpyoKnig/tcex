# -*- coding: utf-8 -*-
"""TcEx Framework TcexJson Object."""
import json
import os
from collections import OrderedDict

import colorama as c

from .install_json import InstallJson


class TcexJson:
    """Object for tcex.json file."""

    def __init__(self, filename=None, path=None):
        """Initialize class properties."""
        self._filename = filename or 'tcex.json'
        self._path = path or os.getcwd()

        # properties
        self._contents = None
        self.ij = InstallJson()

    @property
    def contents(self):
        """Return install.json contents."""
        if self._contents is None:
            try:
                with open(self.filename, 'r') as fh:
                    self._contents = json.load(fh, object_pairs_hook=OrderedDict)
            except OSError:
                self._contents = {}

        # raise error if tcex.json is missing app_name field
        if self._contents and not self._contents.get('package', {}).get('app_name'):
            raise RuntimeError(f'The tcex.json file is missing the package.app_name field.')

        # log warning for old Apps
        if self._contents.get('package', {}).get('app_version'):
            print(
                f'{c.Fore.YELLOW}'
                f'The tcex.json file defines "app_version" which should only be defined\n'
                f'in legacy Apps. Removing the value can cause the App to be treated\n'
                f'as a new App by TcExchange. Please remove "app_version" when appropriate.'
                f'{c.Fore.RESET}'
            )

        return self._contents

    @property
    def filename(self):
        """Return the fqpn for the layout.json file."""
        return os.path.join(self._path, self._filename)

    def update(self):
        """Update the contents of the tcex.json file."""
        with open(self.filename, 'r+') as fh:
            json_data = json.load(fh)

            # update app_name
            json_data = self.update_package_app_name(json_data)

            # update package excludes
            json_data = self.update_package_excludes(json_data)

            # write updated profile
            fh.seek(0)
            fh.write(f'{json.dumps(json_data, indent=2, sort_keys=True)}\n')
            fh.truncate()

        # update contents
        self._contents = json_data

    def update_package_app_name(self, json_data):
        """Update the package app_name in the tcex.json file."""
        if self.package_app_name in [None, '', 'TC_-_', 'TCPB_-_', 'TCVC_-_', 'TCVW_-_']:
            # do a little cleanup on app_name
            app_name = os.path.basename(os.getcwd()).replace(' ', '_').replace('-', '_')
            app_name = '_'.join([a.title() for a in app_name.split('_')])
            if not app_name.startswith(self.ij.app_prefix):
                app_name = f'{self.ij.app_prefix}{app_name}'
            json_data['package']['app_name'] = app_name
        return json_data

    def update_package_excludes(self, json_data):
        """Update the excludes values in the tcex.json file."""
        excludes = self.package_excludes
        excludes.extend(
            [
                '.gitignore',
                '.pre-commit-config.yaml',
                'local-*',
                'pyproject.toml',
                'setup.cfg',
                'tcex.json',
                '*.install.json',
                'tcex.d',
            ]
        )
        excludes = sorted(list(set(excludes)))
        # the requirements.txt file is required for App Builder
        try:
            excludes.remove('requirements.txt')
        except ValueError:
            pass
        json_data['package']['excludes'] = excludes

        return json_data

    #
    # properties
    #

    @property
    def lib_version(self):
        """Return property."""
        return self.contents.get('lib_version', [])

    @property
    def package(self):
        """Return property."""
        return self.contents.get('package', {})

    @property
    def package_app_name(self):
        """Return property."""
        return self.package.get('app_name')

    @property
    def package_app_version(self):
        """Return property."""
        return self.package.get('app_version')

    @property
    def package_bundle(self):
        """Return property."""
        return self.package.get('bundle', False)

    @property
    def package_bundle_name(self):
        """Return property."""
        return self.package.get('bundle_name')

    @property
    def package_bundle_packages(self):
        """Return property."""
        return self.package.get('bundle_packages', [])

    @property
    def package_excludes(self):
        """Return property."""
        return self.package.get('excludes', [])
