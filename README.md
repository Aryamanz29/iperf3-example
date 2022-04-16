# Add iperf bandwidth monitoring check to OpenWISP Monitoring

- On a macro level, the check would work this way:

    - OpenWISP connects to the device (only 1 check per device at time) via SSH and launches iperf3 as a client, first in TCP mode, then in UDP mode, iperf is launched with the **-j flag** to obtain json output.

- The collected data is parsed and stored as a **metric (bandwidth information and jitter)**

- **SSH** connection is closed

## Expected outcomes

- [x] Create Iperf check class.
- [x] Use connection module of openwisp-controller to connect to device using SSH.
- [x] It should be optional and disabled by default.
- [ ] It can be run default every night, and It can be configurable by organization in setting.
- [ ] {WIP} Implement a lock to allow only 1 Iperf check per server at a time.
- [ ] {WIP} Implement logic which creates the metric, chart and alert settings objects.
- [ ] SSH into device, launch Iperf TCP client, repeat for UDP, collect data of both tests in a data structure.
- [ ] Document how this check works.
- [ ] Achieve at least 99% test coverage for this feature.


```python

"""
models.py
"""
def auto_iperf_check_receiver(sender, instance, created, **kwargs):
    """
    Implements OPENWISP_MONITORING_AUTO_IPERF
    The creation step is executed in the background
    """
    # we need to skip this otherwise this task will be executed
    # every time the configuration is requested via checksum
    if not created:
        return
    transaction_on_commit(
        lambda: auto_create_iperf_check.delay(
            model=sender.__name__.lower(),
            app_label=sender._meta.app_label,
            object_id=str(instance.pk),
        )
    )

"""
app.py
"""
if app_settings.AUTO_IPERF:
from .base.models import auto_iperf_check_receiver

post_save.connect(
    auto_iperf_check_receiver,
    sender=load_model('config', 'Device'),
    dispatch_uid='auto_iperf_check',
)

"""
settings.py
"""
....
....
# By default this should be 'False'
AUTO_IPERF = get_settings_value('AUTO_IPERF', True)
IPERF_SERVERS = get_settings_value('IPERF_SERVERS', {
    # Running on my local
    '66fe76b5-c906-4eb6-b466-6ef93492e9af': ['192.168.5.109'],
    #'<org-pk>': ['<ORG_IPERF_SERVER>']
}) 

""" 
task.py
"""

@shared_task
def auto_create_iperf_check(
    model, app_label, object_id, check_model=None, content_type_model=None
):
    """
    Called by openwisp_monitoring.check.models.auto_iperf_check_receiver
    """
    Check = check_model or get_check_model()
    iperf_check_path = 'openwisp_monitoring.check.classes.Iperf'
    has_check = Check.objects.filter(
        object_id=object_id, content_type__model='device', check_type=iperf_check_path
    ).exists()
    # create new check only if necessary
    if has_check:
        return
    content_type_model = content_type_model or ContentType
    ct = content_type_model.objects.get(app_label=app_label, model=model)
    check = Check(
        name='Iperf', is_active=False, check_type=iperf_check_path, content_type=ct, object_id=object_id
    )
    check.full_clean()
    check.save()

""" 
iperf.py
"""

class Iperf(BaseCheck):
    def check(self, store=True):
        # 192.168.5.109
        servers = list(app_settings.IPERF_SERVERS.values())[0][0]
        command = f'iperf3 -c {servers} -J'
        # Check device connection
        try:
            device_connection = DeviceConnection.objects.get(device_id=self.related_object.id)
            if device_connection.enabled and device_connection.is_working:
                device_connection.connect()
                print(f'DEVICE IS CONNECTED, {self.related_object.id}') 
                res, exit_code = device_connection.connector_instance.exec_command(command, raise_unexpected_exit=False)
                if exit_code != 0:
                    print('---- Command Failed ----')
                    print(res[0], type(res))
                    return 
                else:
                    res_dict = self.get_res_data(res) 
                    print('---- Command Output ----')
                    print(res_dict, type(res_dict))
                    if store:
                        self.store_result(res_dict)
                    return result       
            else:
                print(f'{self.related_object}: Connection not properly set')
                return
        # If device have not active connection warning logged (return)
        except ObjectDoesNotExist:
            return
        pass

   def get_res_data(self, res, mode=None):
        res_loads = json.loads(res)
        if mode is None:
            result = {
            'host' : res_loads['start']['connecting_to']['host'],
            'port' : res_loads['start']['connecting_to']['port'],
            'protocol' : res_loads['start']['test_start']['protocol'],
            'duration' : res_loads['start']['test_start']['duration'],

            'sum_sent_bytes' : res_loads['end']['sum_sent']['bytes'],
            'sum_sent_bps' : res_loads['end']['sum_sent']['bits_per_second'],
            'sum_sent_retransmits' : res_loads['end']['sum_sent']['retransmits'],
            'sum_rec_bytes' : res_loads['end']['sum_received']['bytes'],
            'sum_rec_bps' : res_loads['end']['sum_received']['bits_per_second'],
            }
            return result
        # For UDP
        else:
            pass

    def store_result(self, result):
        """
        store result in the DB
        """
        metric = self._get_metric()
        metric.write(result)
    
    def _get_metric(self):
        """
        Gets or creates metric
        """
        metric, created = self._get_or_create_metric()
        if created:
            self._create_charts(metric)
        return metric

    def _create_charts(self, metric):
        """
        Creates Iperf related charts (Bandwith/Jitter)
        """
        charts = ['host', 'port', 'protocol', 'duration', 'sum_sent_bytes', 'sum_sent_bps', 'sum_sent_retransmits', 'sum_rec_bytes', 'sum_rec_bps']
        for chart in charts:
            chart = Chart(metric=metric, configuration=chart)
            chart.full_clean()
            chart.save()
```

## Screenshots

![Screenshot from 2022-04-16 15-23-22](https://user-images.githubusercontent.com/56113566/163670538-6b4c7ab6-978c-470e-aea6-53e1074696ac.png)


![Screenshot from 2022-04-16 13-12-24](https://user-images.githubusercontent.com/56113566/163666668-5fcb700b-1d6e-4a98-84fa-195501a9a737.png)

![Screenshot from 2022-04-16 13-17-02](https://user-images.githubusercontent.com/56113566/163666784-acedc010-c31c-4dbd-9c54-09558c9a7a84.png)

![Screenshot from 2022-04-16 13-12-47](https://user-images.githubusercontent.com/56113566/163666812-8db6fe63-9398-4f60-a287-5fbe78ea441f.png)
