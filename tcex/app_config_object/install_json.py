# -*- coding: utf-8 -*-
"""TcEx Framework InstallJson Object."""
import json
import os
from collections import OrderedDict


class InstallJson:
    """Object for install.json file."""

    def __init__(self, filename=None, path=None):
        """Initialize class properties."""
        self._filename = filename or 'install.json'
        self._path = path or os.getcwd()

        # properties
        self._contents = None

    @staticmethod
    def _to_bool(value):
        """Convert string value to bool."""
        bool_value = False
        if str(value).lower() in ['1', 'true']:
            bool_value = True
        return bool_value

    @property
    def app_output_var_type(self):
        """Return the appropriate output var type for the current App."""
        if self.runtime_level.lower() in ['triggerservice', 'webhooktriggerservice']:
            return 'Trigger'
        return 'App'

    @property
    def contents(self):
        """Return install.json contents."""
        if self._contents is None:
            try:
                with open(self.filename, 'r') as fh:
                    self._contents = json.load(fh, object_pairs_hook=OrderedDict)
            except OSError:
                self._contents = {'runtimeLevel': 'external'}
        return self._contents

    def create_output_variables(self, output_variables, job_id=9876):
        """Create output variables.

        # "#App:9876:app.data.count!String"
        # "#Trigger:9876:app.data.count!String"

        Args:
            output_variables (dict): A dict of the output variables
            job_id (int): A job id to use in output variable string.
        """
        variables = []
        for p in output_variables:
            variables.append(self.create_variable(p.get('name'), p.get('type'), job_id))
        return variables

    def create_variable(self, var_name, var_type, job_id=1234):
        """Create output variables.

        # "#App:9876:app.data.count!String"
        # "#Trigger:9876:app.data.count!String"

        Args:
            var_name (str): The variable name.
            var_type (str): The variable type.
            job_id (int): A job id to use in output variable string.
        """
        return f'#{self.app_output_var_type}:{job_id}:{var_name}!{var_type}'

    @staticmethod
    def expand_valid_values(valid_values):
        """Expand supported playbook variables to their full list.

        Args:
            valid_values (list): The list of valid values for Choice or MultiChoice inputs.

        Returns:
            list: An expanded list of valid values for Choice or MultiChoice inputs.
        """

        if '${GROUP_TYPES}' in valid_values:
            valid_values.remove('${GROUP_TYPES}')
            valid_values.extend(
                [
                    'Adversary',
                    'Campaign',
                    'Document',
                    'Email',
                    'Event',
                    'Incident',
                    'Intrusion Set',
                    'Signature',
                    'Task',
                    'Threat',
                ]
            )
        elif '${OWNERS}' in valid_values:
            valid_values.remove('${OWNERS}')
            valid_values.append('')
        elif '${USERS}' in valid_values:
            valid_values.remove('${USERS}')
            valid_values.append('')
        return valid_values

    @property
    def filename(self):
        """Return the fqpn for the layout.json file."""
        return os.path.join(self._path, self._filename)

    def filter_params_dict(self, name=None, required=None, service_config=None, _type=None):
        """Return params as name/data dict."""
        params = {}
        for p in self.params:

            if name is not None:
                if p.get('name') != name:
                    continue

            if required is not None:
                if p.get('required', False) is not required:
                    continue

            if service_config is not None:
                if p.get('serviceConfig', False) is not service_config:
                    continue

            if _type is not None:
                if p.get('type') is not _type:
                    continue

            params.setdefault(p.get('name'), p)
        return params

    @property
    def optional_params_dict(self):
        """Return params as name/data dict."""
        params = {}
        for p in self.params:
            if p.get('required', False) is False:
                params.setdefault(p.get('name'), p)
        return params

    # TODO: should this be a property
    def output_variables_dict(self):
        """Return output variables as name/data dict."""
        output_variables = {}
        for o in self.contents.get('playbook', {}).get('outputVariables') or []:
            output_variables.setdefault(o.get('name'), o)
        return output_variables

    @property
    def params_dict(self):
        """Return params as name/data dict."""
        params = {}
        for p in self.params:
            params.setdefault(p.get('name'), p)
        return params

    def params_to_args(self, name=None, required=None, service_config=None, _type=None):
        """Return params as cli args."""
        args = {}
        for n, p in self.filter_params_dict(name, required, service_config, _type).items():
            if p.get('type').lower() == 'boolean':
                args[n] = self._to_bool(p.get('default', False))
            elif p.get('type').lower() == 'choice':
                valid_values = '|'.join(self.expand_valid_values(p.get('validValues', [])))
                args[n] = f'[{valid_values}]'
            elif p.get('type').lower() == 'multichoice':
                args[n] = p.get('validValues', [])
            elif p.get('type').lower() == 'keyvaluelist':
                args[n] = '<KeyValueList>'
            elif n in ['api_access_id', 'api_secret_key']:
                # leave these parameters set to the value defined in defaults
                pass
            else:
                types = '|'.join(p.get('playbookDataType', []))
                if types:
                    args[n] = p.get('default', f'<{types}>')
                else:
                    args[n] = p.get('default', '')
        return args

    @property
    def require_params_dict(self):
        """Return params as name/data dict."""
        params = {}
        for p in self.params:
            if p.get('required') is True:
                params.setdefault(p.get('name'), p)
        return params

    @property
    def service_config_params_dict(self):
        """Return params as name/data dict."""
        params = {}
        for p in self.params:
            if p.get('serviceConfig') is True:
                params.setdefault(p.get('name'), p)
        return params

    @property
    def trigger_config_params_dict(self):
        """Return params as name/data dict."""
        params = {}
        for p in self.params:
            if p.get('serviceConfig', False) is False:
                params.setdefault(p.get('name'), p)
        return params

    def update_schema(self, migrate=False):
        """Update the profile to the current schema."""
        with open(os.path.join(self.filename), 'r+') as fh:
            json_data = json.load(fh)

            # update all env variables to match latest pattern
            json_data = self.update_schema_features(json_data)

            if migrate:
                json_data = self.update_schema_program_main(json_data)

            # write updated profile
            fh.seek(0)
            fh.write(f'{json.dumps(json_data, indent=2, sort_keys=True)}\n')

    def update_schema_features(self, json_data):
        """Update feature set based on App type."""
        features = self.features
        if self.runtime_level.lower() in ['playbook']:
            features = ['aotExecutionEnabled', 'appBuilderCompliant', 'secureParams']
        elif self.runtime_level.lower() in ['triggerservice', 'webhooktriggerservice']:
            features = ['appBuilderCompliant', 'fileParams', 'secureParams']

        json_data['features'] = features

        return json_data

    def update_schema_program_main(self, json_data):
        """Update program main on App type."""
        if self.program_main:
            if self.runtime_level.lower() in ['playbook']:
                json_data['programMain'] = 'run'
            if self.runtime_level.lower() in ['triggerservice', 'webhooktriggerservice']:
                json_data['programMain'] = 'run.py'

        return json_data

    #
    # properties
    #

    @property
    def allow_on_demand(self):
        """Return property."""
        return self.contents.get('allowOnDemand', False)

    @property
    def commit_hash(self):
        """Return property."""
        return self.contents.get('commitHash')

    @property
    def display_name(self):
        """Return property."""
        return self.contents.get('displayName')

    @property
    def features(self):
        """Return property."""
        return self.contents.get('features', [])

    @property
    def feeds(self):
        """Return property."""
        return self.contents.get('feeds', {})

    @property
    def labels(self):
        """Return property."""
        return self.contents.get('labels', [])

    @property
    def language_version(self):
        """Return property."""
        return self.contents.get('languageVersion')

    @property
    def list_delimiter(self):
        """Return property."""
        return self.contents.get('listDelimiter')

    @property
    def min_server_version(self):
        """Return property."""
        return self.contents.get('minServerVersion')

    @property
    def note(self):
        """Return property."""
        return self.contents.get('note')

    @property
    def output_variable_array(self):
        """Return playbook output variable name array"""
        return self.create_output_variables(self.output_variables)

    @property
    def output_variable_csv_string(self):
        """Return playbook output variables as CSV string"""
        return ','.join(self.output_variable_array)

    @property
    def output_variables(self):
        """Return output variables as name/data dict."""
        return self.playbook.get('outputVariables', [])

    @property
    def params(self):
        """Return property."""
        return self.contents.get('params', [])

    @property
    def playbook(self):
        """Return property."""
        return self.contents.get('playbook', {})

    @property
    def program_icon(self):
        """Return property."""
        return self.contents.get('programIcon')

    @property
    def program_language(self):
        """Return property."""
        return self.contents.get('programLanguage')

    @property
    def program_main(self):
        """Return property."""
        return self.contents.get('programMain')

    @property
    def program_name(self):
        """Return property."""
        return self.contents.get('programName')

    @property
    def program_version(self):
        """Return property."""
        return self.contents.get('programVersion')

    @property
    def publish_out_files(self):
        """Return property."""
        return self.contents.get('publishOutFiles')

    @property
    def repeating_minutes(self):
        """Return property."""
        return self.contents.get('repeatingMinutes')

    @property
    def runtime_context(self):
        """Return property."""
        return self.contents.get('runtimeContext')

    @property
    def runtime_level(self):
        """Return property."""
        return self.contents.get('runtimeLevel')
