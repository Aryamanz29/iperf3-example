import subprocess

from django.core.exceptions import ValidationError
from jsonschema import draft7_format_checker, validate
from jsonschema.exceptions import ValidationError as SchemaError
from swapper import load_model

from openwisp_utils.utils import deep_merge_dicts

from ... import settings as monitoring_settings
from .. import settings as app_settings
from ..exceptions import OperationalError
from .base import BaseCheck
from openwisp_controller.connection.connectors import ssh

Chart = load_model('monitoring', 'Chart')
Metric = load_model('monitoring', 'Metric')
Device = load_model('config', 'Device')
DeviceData = load_model('device_monitoring', 'DeviceData')
Credentials = load_model('connection', 'Credentials')
AlertSettings = load_model('monitoring', 'AlertSettings')

class Iperf(BaseCheck):

    def check(self, store=True):
        pass

    def store_result(self, result):
        pass
    def _get_param(self, param):
        pass

    def _get_ip(self):
        pass
    def _command(self, command):
        pass
    def _get_metric(self):
       pass
    def _create_alert_settings(self, metric):
        pass
    def _create_charts(self, metric):
        pass