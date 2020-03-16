#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TcEx Framework Test Generation Module."""
import json
import os
from random import randint

from .bin import Bin
from ..app_config_object import Profile, ProfileInteractive
from ..app_config_object.templates import (
    CustomTemplates,
    DownloadTemplates,
    TestProfileTemplates,
    ValidationTemplates,
)


class Test(Bin):
    """Create testing files for ThreatConnect Exchange App.

    Args:
        _args (namespace): The argparser args Namespace.
    """

    def __init__(self, _args):
        """Initialize Class properties."""
        super().__init__(_args)

        # properties
        self.profile = Profile(
            default_args={}, feature=self.args.feature, name=self.args.profile_name
        )
        self.custom_templates = CustomTemplates(self.profile, self.args.branch)
        self.download_template = DownloadTemplates(self.args.branch, self.profile)
        self.profile_interactive = ProfileInteractive(self.profile)
        self.test_profile_template = TestProfileTemplates(self.profile, self.args.branch)
        self.validation_templates = ValidationTemplates(self.profile, self.args.branch)

    def add_profile(self):
        """Add the desired profile"""
        sort_keys = True
        if self.args.profile_file:
            sort_keys = False
            data = []
            profile_file = os.path.join(self.app_path, 'tcex.d', 'profiles', self.args.profile_file)
            if os.path.isfile(self.args.profile_file):
                with open(self.args.profile_file, 'r') as fh:
                    data = json.load(fh)
            elif os.path.isfile(profile_file):
                with open(profile_file, 'r') as fh:
                    data = json.load(fh)
            else:
                self.handle_error(f'Error reading in profile file: {self.args.profile_file}', True)

            profile_data = {}
            for d in data:
                profile_data[d.get('profile_name')] = {
                    'exit_codes': d.get('exit_codes'),
                    'exit_message': None,
                    'inputs': d.get('args', {}).get('app'),
                    'runtime_level': self.ij.runtime_level,
                    'stage': {'kvstore': self.load_legacy_profiles(d.get('data_files', []))},
                }

        elif self.ij.runtime_level.lower() == 'playbook' and self.args.permutation_id is not None:
            profile_data = {
                self.args.profile_name: {
                    'inputs': {
                        'optional': self.profile_settings_args_layout_json(False),
                        'required': self.profile_settings_args_layout_json(True),
                    },
                    'output_variables': self.permutations.output_permutations[
                        self.args.permutation_id
                    ],
                    'runtime_level': self.ij.runtime_level,
                }
            }
        elif self.ij.runtime_level.lower() == 'triggerservice':
            config = self.ij.params_to_args(service_config=False)
            if self.args.permutation_id is not None:
                config = self.profile_settings_args_layout_json(True)
                config.update(self.profile_settings_args_layout_json(False))

            profile_data = {
                self.args.profile_name: {
                    'configs': [{'trigger_id': str(randint(1000, 9999)), 'config': config}],
                    'runtime_level': self.ij.runtime_level,
                    'trigger': {},
                }
            }
        elif self.ij.runtime_level.lower() == 'webhooktriggerservice':
            config = self.ij.params_to_args(service_config=False)
            if self.args.permutation_id is not None:
                config = self.profile_settings_args_layout_json(True)
                config.update(self.profile_settings_args_layout_json(False))

            profile_data = {
                self.args.profile_name: {
                    'configs': [{'trigger_id': str(randint(1000, 9999)), 'config': config}],
                    'runtime_level': self.ij.runtime_level,
                    'webhook_event': {
                        'body': '',
                        'headers': [],
                        'method': 'GET',
                        'query_params': [],
                        'trigger_id': '',
                    },
                }
            }
        else:
            profile_data = {
                self.args.profile_name: {
                    'inputs': {
                        'optional': self.ij.params_to_args(required=False),
                        'required': self.ij.params_to_args(required=True),
                    },
                    'runtime_level': self.ij.runtime_level,
                }
            }

        # add profiles
        for profile_name, data in profile_data.items():
            self.profile.add(profile_data=data, profile_name=profile_name, sort_keys=sort_keys)

    def create_dirs(self):
        """Create tcex.d directory and sub directories."""
        for d in [
            self.profile.test_directory,
            self.profile.feature_directory,
            self.profile.directory,
        ]:
            if not os.path.isdir(d):
                os.makedirs(d)

        # create __init__ files
        self.create_dirs_init()

    def create_dirs_init(self):
        """Create the __init__.py file under dir."""
        for d in [self.profile.test_directory, self.profile.feature_directory]:
            if os.path.isdir(d):
                with open(os.path.join(d, '__init__.py'), 'a'):
                    os.utime(os.path.join(d, '__init__.py'), None)

    def interactive_profile(self):
        """Present interactive profile inputs."""
        self.profile_interactive.present()
        # BCS
        profile_data = {
            'inputs': self.profile_interactive.inputs,
            'runtime_level': self.ij.runtime_level,
            'stage': self.profile_interactive.staging_data,
        }
        self.profile.add(profile_data=profile_data)

    @staticmethod
    def load_legacy_profiles(staging_files):
        """Load staging data to migrate legacy templates."""
        staging_data = {}
        for sf in staging_files:
            with open(sf, 'r') as fh:
                data = json.load(fh)
            for d in data:
                staging_data[d.get('variable')] = d.get('data')
        return staging_data
