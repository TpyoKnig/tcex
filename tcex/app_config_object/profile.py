# -*- coding: utf-8 -*-
"""TcEx testing profile Class."""
import json
import os
import re
import sys

import hvac
import jmespath

from .install_json import InstallJson
from .layout_json import LayoutJson
from .permutations import Permutations


class Profile:
    """Testing Profile Class.

    Args:
        feature (str, optional): The feature name. Defaults to None.
        name ([type], optional): The filename of the profile
            in the profile.d director. Defaults to None.
    """

    def __init__(
        self,
        default_args,
        feature=None,
        name=None,
        redis_client=None,
        replace_exit_message=False,
        replace_outputs=False,
        tcex_testing_context=None,
    ):
        """Initialize Class properties."""
        self._default_args = default_args
        self._feature = feature
        self._name = name
        self.replace_exit_message = replace_exit_message
        self.replace_outputs = replace_outputs
        self.tcex_testing_context = tcex_testing_context

        # properties
        self._app_path = os.getcwd()
        self._data = None
        self._output_variables = None
        self._context_tracker = []
        self.ij = InstallJson()
        self.lj = LayoutJson()
        self.permutations = Permutations()
        self.redis_client = redis_client
        self.tc_staged_data = {}
        self.vault_client = hvac.Client(
            url=os.getenv('VAULT_URL', 'http://localhost:8200'),
            token=os.getenv('VAULT_TOKEN'),
            cert=os.getenv('VAULT_CERT'),
        )

    @property
    def _test_case_data(self):
        """Return partially parsed test case data."""
        return os.getenv('PYTEST_CURRENT_TEST').split(' ')[0].split('::')

    @property
    def _test_case_name(self):
        """Return partially parsed test case data."""
        return self._test_case_data[-1].replace('/', '-').replace('[', '-').replace(']', '')

    def add(self, profile_data, profile_name=None, sort_keys=True):
        """Add a profile."""
        if profile_name is not None:
            # only used for profile migrations
            self.name = profile_name

        if os.path.isfile(self.filename):
            print('A profile with the name already exists.')
            sys.exit(1)

        profile = {
            'exit_codes': profile_data.get('exit_codes', [0]),
            'exit_message': None,
            'outputs': profile_data.get('outputs'),
            'stage': profile_data.get('stage', {'redis': {}, 'threatconnect': {}}),
        }
        if self.ij.runtime_level.lower() == 'triggerservice':
            profile['configs'] = profile_data.get('configs')
            profile['trigger'] = profile_data.get('trigger')
        elif self.ij.runtime_level.lower() == 'webhooktriggerservice':
            profile['configs'] = profile_data.get('configs')
            profile['webhook_event'] = profile_data.get('webhook_event')
        else:
            profile['inputs'] = profile_data.get('inputs')

        if self.ij.runtime_level.lower() == 'organization':
            profile['validation_criteria'] = profile_data.get('validation_criteria', {'percent': 5})
            profile.pop('outputs')

        with open(self.filename, 'w') as fh:
            json.dump(profile, fh, indent=2, sort_keys=sort_keys)

    def add_context(self, context):
        """Add a context to the context tracker for this profile.

        Args:
            context (str): The context (session_id) for this profile.
        """
        self._context_tracker.append(context)

    def clear_context(self, context):
        """Delete all context data in redis"""
        keys = self.redis_client.hkeys(context)
        if keys:
            return self.redis_client.hdel(context, *keys)
        return 0

    @property
    def context_tracker(self):
        """Return the current context trackers for Service Apps."""
        if not self._context_tracker:
            self._context_tracker = json.loads(
                self.redis_client.hget(self.tcex_testing_context, '_context_tracker') or '[]'
            )
        return self._context_tracker

    @property
    def data(self):
        """Return the Data (dict) from the current profile."""
        if self._data is None:
            try:
                with open(os.path.join(self.filename), 'r') as fh:
                    profile_data = json.load(fh)

                    # update profile schema
                    profile_data = self.update_schema(profile_data)

                    # replace all variable references
                    profile_data = self.replace_env_variables(profile_data)

                    # replace all staged variable
                    profile_data = self.replace_tc_variables(profile_data)

                    # set update profile data
                    self._data = profile_data

            except OSError:
                print(f'Could not open profile {self.filename}.')
        self._data['name'] = self.name
        return self._data

    @data.setter
    def data(self, profile_data):
        """Set profile_data dict."""
        self._data = profile_data

    def delete(self):
        """Delete an existing profile."""
        raise NotImplementedError('The delete method is not currently implemented.')

    @property
    def directory(self):
        """Return fully qualified profile directory."""
        return os.path.join(self._app_path, 'tests', self.feature, 'profiles.d')

    @property
    def feature_directory(self):
        """Return fully qualified feature directory."""
        return os.path.join(self._app_path, 'tests', self.feature)

    @property
    def filename(self):
        """Return profile fully qualified filename."""
        return os.path.join(self.directory, f'{self.name}.json')

    @property
    def feature(self):
        """Return the current feature."""
        if self._feature is None:
            # when called in testing framework get the feature from pytest env var.
            self._feature = self._test_case_data[0].split('/')[1].replace('/', '-')
        return self._feature

    @property
    def name(self):
        """Return partially parsed test case data."""
        if self._name is None:
            name_pattern = r'^test_[a-zA-Z0-9_]+\[(.+)\]$'
            self._name = re.search(name_pattern, self._test_case_data[-1]).group(1)
        return self._name

    @name.setter
    def name(self, name):
        """Set the profile name"""
        self._name = name

    @property
    def test_directory(self):
        """Return fully qualified test directory."""
        return os.path.join(self._app_path, 'tests')

    def update(self):
        """Update an existing profile."""
        raise NotImplementedError('The update method is not currently implemented.')

    def update_exit_message(self):
        """Update validation rules from exit_message section of profile."""
        message_tc = ''
        if os.path.isfile(self.message_tc_filename):
            with open(self.message_tc_filename, 'r') as mh:
                message_tc = mh.read()

        with open(self.filename, 'r+') as fh:
            profile_data = json.load(fh)

            if (
                profile_data.get('exit_message') is None
                or isinstance(profile_data.get('exit_message'), str)
                or self.replace_exit_message
            ):
                # update the profile
                profile_data['exit_message'] = {'expected_output': message_tc, 'op': 'eq'}

                fh.seek(0)
                fh.write(json.dumps(profile_data, indent=2, sort_keys=True))
                fh.truncate()

    def update_outputs(self):
        """Update the validation rules for outputs section of a profile.

        By default this method will only update if the current value is null. If the
        flag --update_outputs is passed to pytest (e.g., pytest --update_args) the
        outputs will updated regardless of their current value.
        """
        if self.redis_client is None:
            # redis_client is only available for children of TestCasePlaybookCommon
            print('An instance of redis_client is not set.')
            sys.exit(1)

        with open(self.filename, 'r+') as fh:
            profile_data = json.load(fh)

            output_variables = self.ij.output_variable_array
            if self.lj.has_layout:
                # if layout based App get valid outputs
                output_variables = self.ij.create_output_variables(
                    self.permutations.outputs_by_inputs(self.args)
                )

            outputs = {}
            for context in self.context_tracker:
                # get all current keys in current context
                redis_data = self.redis_client.hgetall(context)
                trigger_id = self.redis_client.hget(context, '_trigger_id')

                # updated outputs with validation data
                self.update_outputs_variables(outputs, output_variables, redis_data, trigger_id)

                # cleanup redis
                self.clear_context(context)

            print('self.replace_outputs', self.replace_outputs)
            # write updated profile
            if self.outputs is None or self.replace_outputs:
                profile_data['outputs'] = outputs
                fh.seek(0)
                fh.write(f'{json.dumps(profile_data, indent=2, sort_keys=True)}\n')

        # update _data dict with updated profile
        self._data = json.dumps(profile_data)

    def update_outputs_variables(self, outputs, output_variables, redis_data, trigger_id):
        """Return the outputs section of a profile.

        Args:
            outputs (dict): The dict to add outputs.
            output_variables (list): A valid list of output variables for this profile.
            redis_data (dict): The data from KV store for this profile.
            trigger_id (str): The current trigger_id (service Apps).
        """

        for variable in self.ij.output_variable_array:
            if variable not in output_variables:
                continue

            # get data from redis for current context
            data = redis_data.get(variable.encode('utf-8'))

            # validate redis variables
            if data is None:
                # log error for missing output data
                # self.log.error(
                #     f'[{self.profile_name}] Missing redis output for variable {variable}'
                # )
                print(f'[{self.name}] Missing redis output for variable {variable}')
            else:
                data = json.loads(data.decode('utf-8'))

            # validate validation variables
            validation_data = (self.outputs or {}).get(variable)
            if trigger_id is None and validation_data is None and self.outputs:
                # self.log.error(f'[{self.profile_name}] Missing validations rule: {variable}')
                print(f'[{self.name}] Missing validations rule: {variable}')

            # make business rules based on data type or content
            output_data = {'expected_output': data, 'op': 'eq'}
            if variable.endswith('json.raw!String'):
                output_data['exclude'] = []
                output_data['op'] = 'jeq'

            # get trigger id for service Apps
            if trigger_id is not None:
                if isinstance(trigger_id, bytes):
                    trigger_id = trigger_id.decode('utf-8')
                outputs.setdefault(trigger_id, {})
                outputs[trigger_id][variable] = output_data
            else:
                outputs[variable] = output_data

    def replace_env_variables(self, profile_data):
        """Update the profile to the current schema.

        Args:
            profile_data (dict): The profile data dict.

        Returns:
            dict: The updated dict.
        """
        profile = json.dumps(profile_data)

        for m in re.finditer(r'\${(env|os|vault):(.*?)}', profile):
            try:
                full_match = m.group(0)
                env_type = m.group(1)  # currently env, os, or vault
                env_key = m.group(2)

                if env_type in ['env', 'os'] and os.getenv(env_key):
                    profile = profile.replace(full_match, env_key)
                elif env_type in ['env', 'vault'] and self.vault_client.read(env_key):
                    profile = profile.replace(full_match, self.vault_client.read(env_key))
            except IndexError:
                print(f'Invalid variable found {full_match}.')
        return json.loads(profile)

    def replace_tc_variables(self, profile_data):
        """Replace all of the TC output variables in the profile with their correct value.

        Args:
            profile_data (dict): The profile data dict.

        Returns:
            dict: The updated dict.
        """
        profile = json.dumps(profile_data)

        for key, value in self.tc_staged_data.items():
            for m in re.finditer(r'\${tcenv:' + str(key) + r':(.*?)}', profile):
                try:
                    full_match = m.group(0)
                    jmespath_expression = m.group(1)

                    if jmespath_expression:
                        value = jmespath.search(jmespath_expression, value)
                        profile = profile.replace(full_match, str(value))
                except IndexError:
                    print(f'Invalid variable found {full_match}.')
        return json.loads(profile)

    def update_schema(self, profile_data):
        """Update the profile to the current schema."""
        with open(self.filename, 'r+') as fh:

            # update all env variables to match latest pattern
            profile_data = self.update_schema_variable_pattern_env(profile_data)

            # update all tcenv variables to match latest pattern
            profile_data = self.update_schema_variable_pattern_tcenv(profile_data)

            # schema change for threatconnect staged data
            profile_data = self.update_schema_stage_redis_name(profile_data)

            # schema change for threatconnect staged data
            profile_data = self.update_schema_stage_threatconnect_data(profile_data)

            # write updated profile
            fh.seek(0)
            fh.write(f'{json.dumps(profile_data, indent=2, sort_keys=True)}\n')

        return profile_data

    @staticmethod
    def update_schema_variable_pattern_env(profile_data):
        """Update the profile variable to latest pattern

        Args:
            profile_data (dict): The profile data dict.

        Returns:
            dict: The updated dict.
        """
        profile = json.dumps(profile_data)

        for m in re.finditer(r'\${(env|os|vault)\.(.*?)}', profile):
            try:
                full_match = m.group(0)
                env_type = m.group(1)  # currently env, os, or vault
                env_key = m.group(2)

                new_variable = f'${{{env_type}:{env_key}}}'
                profile = profile.replace(full_match, new_variable)
            except IndexError:
                print(f'Invalid variable found {full_match}.')
        return json.loads(profile)

    def update_schema_variable_pattern_tcenv(self, profile_data):
        """Update the profile variable to latest pattern

        Args:
            profile_data (dict): The profile data dict.

        Returns:
            dict: The updated dict.
        """
        profile = json.dumps(profile_data)

        for key in self.tc_staged_data:
            for m in re.finditer(r'\${tcenv\.' + str(key) + r'\.(.*?)}', profile):
                try:
                    full_match = m.group(0)
                    jmespath_expression = m.group(1)

                    new_variable = f'${{tcenv:{key}:{jmespath_expression}}}'
                    profile = profile.replace(full_match, new_variable)
                except IndexError:
                    print(f'Invalid variable found {full_match}.')
        return json.loads(profile)

    @staticmethod
    def update_schema_stage_redis_name(profile_data):
        """Update the schema for stage redis to kvstore

        This schema change updates the previous value of redis with a
        more generic value of kvstore for staged data.

        Args:
            profile_data (dict): The current profile data dict.

        Returns:
            dict: The update profile dict.
        """
        if profile_data.get('stage') is None:
            return profile_data

        kvstore_data = profile_data.get('stage').pop('redis', None)
        if kvstore_data:
            profile_data['stage']['kvstore'] = kvstore_data

        return profile_data

    @staticmethod
    def update_schema_stage_threatconnect_data(profile_data):
        """Update the schema for stage threatconnect data section of profile

        This schema change updates the previous list to a dict with a key that
        can be reference as a variable in other sections of the profile.

        Args:
            profile_data (dict): The current profile data dict.

        Returns:
            dict: The update profile dict.
        """
        if 'stage' not in profile_data:
            return profile_data

        stage_tc = profile_data.get('stage').get('threatconnect')

        # check if profile is using old list type
        if isinstance(stage_tc, list):
            profile_data['stage']['threatconnect'] = {}

            counter = 0
            for item in stage_tc:
                profile_data['stage']['threatconnect'][f'item_{counter}'] = item
                counter += 1

        return profile_data

    #
    # Properties
    #

    @property
    def args(self):
        """Return combined optional and required args."""
        args = self.inputs_optional
        args.update(self.inputs_required)
        return dict(args)

    @property
    def configs(self):
        """Return environments."""
        return list(self.data.get('configs', []))

    @property
    def environments(self):
        """Return environments."""
        return self.data.get('environments', ['build'])

    @property
    def exit_codes(self):
        """Return exit codes."""
        return self.data.get('exit_codes', [])

    @property
    def exit_message(self):
        """Return exit message dict."""
        return self.data.get('exit_message', {})

    @property
    def inputs(self):
        """Return inputs dict."""
        return self.data.get('inputs', {})

    @property
    def inputs_optional(self):
        """Return required inputs dict."""
        return self.inputs.get('optional')

    @property
    def inputs_required(self):
        """Return required inputs dict."""
        return self.inputs.get('required')

    @property
    def message_tc_filename(self):
        """Return the fqpn for message_tc file relative to profile."""
        return os.path.join(
            self._default_args.get('tc_out_path'), self.feature, self._test_case_name, 'message.tc'
        )

    @property
    def owner(self):
        """Return the owner value."""
        return (
            self.data.get('required', {}).get('owner')
            or self.data.get('optional', {}).get('owner')
            or self.data.get('owner')
        )

    @property
    def outputs(self):
        """Return outputs dict."""
        return self.data.get('outputs')

    @property
    def stage(self):
        """Return stage dict."""
        return self.data.get('stage', {})

    @property
    def stage_kvstore(self):
        """Return stage kv store dict."""
        return self.stage.get('kvstore', {})

    @property
    def stage_threatconnect(self):
        """Return stage threatconnect dict."""
        return self.stage.get('threatconnect', {})

    @property
    def tc_in_path(self):
        """Return fqpn tc_in_path arg relative to profile."""
        return os.path.join(self._default_args.get('tc_in_path'), self.feature)

    @property
    def tc_log_path(self):
        """Return fqpn tc_log_path arg relative to profile."""
        return os.path.join(
            self._default_args.get('tc_log_path'), self.feature, self._test_case_name
        )

    def tc_playbook_out_variables(self):
        """Return all output variables for this profile."""
        return self.ij.output_variable_csv_string

    @property
    def tc_out_path(self):
        """Return fqpn tc_out_path arg relative to profile."""
        return os.path.join(
            self._default_args.get('tc_out_path'), self.feature, self._test_case_name
        )

    @property
    def tc_temp_path(self):
        """Return fqpn tc_temp_path arg relative to profile."""
        return os.path.join(
            self._default_args.get('tc_temp_path'), self.feature, self._test_case_name
        )

    @property
    def validate_criteria(self):
        """Return outputs dict."""
        return self.data.get('validate_criteria', {})

    @property
    def webhook_event(self):
        """Return outputs dict."""
        return self.data.get('webhook_event', {})
