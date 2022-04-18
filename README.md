# Add iperf bandwidth monitoring check to OpenWISP Monitoring

- On a macro level, the check would work this way:

    - OpenWISP connects to the device (only 1 check per device at time) via SSH and launches iperf3 as a client, first in TCP mode, then in UDP mode, iperf is launched with the **-j flag** to obtain json output.

- The collected data is parsed and stored as a **metric (bandwidth information and jitter)**

- **SSH** connection is closed.
![-------------------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## Approach : 
 
 - [x] Create `Iperf` check class.
    
    - We can extend [BaseCheck](https://github.com/openwisp/openwisp-monitoring/blob/8a1706f15a91491f816962159c7ea1603412bfba/openwisp_monitoring/check/classes/base.py#L10) for `openwisp_monitoring/check/classes/iperf.py`
    
    - Using [DeviceConnection](https://github.com/openwisp/openwisp-controller/blob/487641b95cbda4580f19b0b1e6515f6a264e65fa/openwisp_controller/connection/base/models.py#L210) & [Device](https://github.com/openwisp/openwisp-controller/blob/487641b95cbda4580f19b0b1e6515f6a264e65fa/openwisp_controller/config/base/device.py#L18) `(openwisp-controller/connection)` we can check if device has a active connection or not.

    ```py
    #For ex
    try:
        device_connection = DeviceConnection.objects.get(
                    device_id=self.related_object.id
                ) 
        if device_connection.enabled and device_connection.is_working:
            # Do something
        else :
            # Connection not properly set
        
        # If device have not active connection warning logged (return)
        except ObjectDoesNotExist:
            logger.warning(f'{self.related_object}: Device has no active connection, Iperf skip')
            return
    ```
 - [x] Allow configuring the iperf server globally and by organization with a setting,
    - User can configure multiple iperf servers corresponding to `organization`
    ```py
        AUTO_IPERF = get_settings_value('AUTO_IPERF', True)
        IPERF_SERVERS = get_settings_value(
        'IPERF_SERVERS',
        {
            # Running on my local
            '66fe76b5-c906-4eb6-b466-6ef93492e9af': ['172.19.0.1'],
            #'<org-pk>': ['<ORG_IPERF_SERVER>']
        },)
        # In iperf.py 
        # For ex (need to make more configurable)
        servers = list(app_settings.IPERF_SERVERS.values())[0][0]

    ```
 - [x] This check should be optional and disabled by default.
    - Celery task [create_iperf_check](https://github.com/Aryamanz29/iperf3-example/blob/b89531b35ceb1ae47fa21ba5b67bdd3a78f4d652/openwisp-monitoring/openwisp_monitoring/check/tasks.py#L106) is called when new device is registered to create iperf check, Setted `is_active=False`
    ```python
      if has_check:
        return
        content_type_model = content_type_model or ContentType
        ct = content_type_model.objects.get(app_label=app_label, model=model)
        check = Check(
            name='Iperf',
            is_active=False,
            check_type=iperf_check_path,
            content_type=ct,
            object_id=object_id,
        )
        check.full_clean()
        check.save()
    ```

 - [x] We can run it by default every night.
    - Using celery [crontab schedules](https://docs.celeryq.dev/en/latest/userguide/periodic-tasks.html#crontab-schedules) we can configure check task to run on specific time, It also covers most of the time variations for scheduling celery tasks.
    ```python
    # Ex.
    # Task schedule for 5 AM and 12 PM
    @periodic_task(run_every=crontab(minute=0, hour='5,12'))
    ```

 - [x] Handle failures, if server is down, we can store 0, which would trigger an alert (investigate the alert settings functionality)
    - Using `exit_code` of executed commands on device we can handle this case (Todo: Need to explore  more better option)
    ```py
     res, exit_code = device_connection.connector_instance.exec_command(
                    command, raise_unexpected_exit=False
                )
         if exit_code != 0:
                    ## command_exec fails
                    if store:
                        self.store_result(
                            {
                                'iperf_result': 0,
                                'sum_sent_bps': 0.0,
                                'sum_rec_bps': 0.0
                                ...
                                ...
                            }
    ```
 - [x] Implement logic which creates the metric, chart and alert settings objects
    - Currently iperf data extracted from json output of executed command that run on devices.
    ```py
    # Example
     res_loads = json.loads(res)
        if mode is None:
            result = {
                #  
                # 'host' : res_loads['start']['connecting_to']['host'],
                # 'port' : res_loads['start']['connecting_to']['port'],
                # 'protocol' : res_loads['start']['test_start']['protocol'],
                # 'duration' : res_loads['start']['test_start']['duration'],
                'iperf_result': 1,
                # Bandwith in Gbps
                'sum_sent_bps': round(
                    res_loads['end']['sum_sent']['bits_per_second'] / 1000000000, 2
                ),
                'sum_rec_bps': round(
                    res_loads['end']['sum_received']['bits_per_second'] / 1000000000, 2
                ),
                ...
                ...
    ```
    - First metric get created using `self._get_or_create_metric()` followed by charts then result (dict) will be use to write into timeseries database.

    ```py
     metric, created = self._get_or_create_metric()
        if created:
            self._create_charts(metric)
        return metric

        charts = ['bps', 'transfer', 'retransmits']
        for chart in charts:
            chart = Chart(metric=metric, configuration=chart)
            chart.full_clean()
            chart.save()

    ```
    
    - Define `metric configuration` or use  `register_metric().`
    
    ```py
        'iperf': {
            'label': _('Iperf'),
            'name': 'Iperf',
            'key': 'iperf',
            'field_name': 'iperf_result',
            'related_fields': [
                'sum_sent_bps',
                'sum_rec_bps',
                'sum_sent_bytes',
                'sum_rec_bytes',
                'sum_sent_retransmits',
            ],
            'charts': {
                'bps': {
                    'type': 'scatter',
                    'title': _('Bits per second'),
                    'colors': (DEFAULT_COLORS[0], DEFAULT_COLORS[8]),
                    'description': _('Iperf3 bits per second in TCP mode.'),
                    'summary_labels': [
                        _('Sent BPS'),
                        _('Received BPS'),
                    ],
                    'unit': _(' Gbps'),
                    'order': 280,
                    'query': chart_query['bps'],
                },
                'transfer': {
                    'type': 'scatter',
                    'title': _('Transfer'),
                    'colors': (DEFAULT_COLORS[9], DEFAULT_COLORS[6]),
                    'description': _('Iperf3 transfer in TCP mode.'),
                    'summary_labels': [
                        _('Sent Bytes'),
                        _('Received Bytes'),
                    ],
                    'unit': _(' GBytes'),
                    'order': 290,
                    'query': chart_query['transfer'],
                },
                'retransmits': {
                    'type': 'bar',
                    'title': _('Retransmits'),
                    'colors': (DEFAULT_COLORS[4]),
                    'description': _('No. of retransmits during Iperf3 test in TCP mode.'),
                    'unit': '',
                    'order': 300,
                    'query': chart_query['retransmits'],
                },
            },
        },
    }
    ```

 - [x] Save data (tcp max bandwidth, UDP jitter).
    - Perform similar test in UDP `ie. command = f'iperf3 -u -c {servers} -J'` followed by creation of metric and charts and saving test data.
 
 - [x] To Implement a lock (1 iperf check per server at time)
    - For this I've found some good references that I need to first discuss with project mentors. 
    - References :
        - https://docs.celeryq.dev/en/latest/tutorials/task-cookbook.html#ensuring-a-task-is-only-executed-one-at-a-time 
        - https://stackoverflow.com/questions/12003221/celery-task-schedule-ensuring-a-task-is-only-executed-one-at-a-time


![-------------------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

 ### Prerequisites before testing this check : 

 1. Make sure your client (openwrt-device) and server both have [Iperf3](https://iperf.fr/iperf-download.php) installed.  
 ```bash
# server
$ iperf3 --version
iperf 3.9 (cJSON 1.7.13)

#client
root@vm-openwrt:~ iperf3 --version
iperf 3.7 (cJSON 1.5.2)
Linux vm-openwrt 4.14.171 #0 SMP Thu Feb 27 21:05:12 2020 x86_64
Optional features available: CPU affinity setting, IPv6 flow label, TCP congestion algorithm setting, sendfile / zerocopy, socket pacing
 ```

 **NOTE :** The host can by specified by hostname, IPv4 literal, or IPv6 literal
```
# for ex
              iperf3 -c iperf3.example.com

              iperf3 -c 192.0.2.1

              iperf3 -c 2001:db8::1
```

 - In `settings.py` configure this : 
 ```python
 # My local config
 IPERF_SERVERS = get_settings_value(
    'IPERF_SERVERS',
    {
        '66fe76b5-c906-4eb6-b466-6ef93492e9af': ['172.19.0.1'],
        #'<org-pk>': ['<ORG_IPERF_SERVER>']
    },
)
 ```
 2. Do check `credential section` of device (It must be enabled and working)

![Screenshot from 2022-04-18 15-58-26](https://user-images.githubusercontent.com/56113566/163795957-1c29a53f-f8e4-4130-9daa-0a8ff0b4c2c5.png)


 3. Make sure iperf3 running on server.
 ```bash
 iperf -s
 Server listening on 5201
-----------------------------------------------------------
 ```
 4. Follow [installing-for-dev](https://github.com/openwisp/openwisp-monitoring#installing-for-development) section of [openwisp-monitoring.](https://github.com/openwisp/openwisp-monitoring)

### `NOTE:` Alternate repo for demo code (branch : iperf3) - https://github.com/Aryamanz29/openwisp-monitoring/tree/iperf3 

![-------------------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## Screenshots & Demo (Use Chrome browser) :


https://user-images.githubusercontent.com/56113566/163798227-0d30c91b-8741-4e32-8fdb-d6dc315bd3ee.mp4


#### - By default this check is `disabled.`

![Screenshot from 2022-04-18 14-54-39](https://user-images.githubusercontent.com/56113566/163787971-d6d3001f-2687-4982-ae4a-b040e458c15b.png)

#### - `Charts generated` by Iperf check.


![Screenshot from 2022-04-18 15-04-14](https://user-images.githubusercontent.com/56113566/163789635-33bcd68d-31b7-44d7-83ae-6d51ce56723a.png)

![Screenshot from 2022-04-18 15-04-24](https://user-images.githubusercontent.com/56113566/163789639-c471b475-98d0-4c57-9e1f-bc1277ca6352.png)

![Screenshot from 2022-04-18 15-04-42](https://user-images.githubusercontent.com/56113566/163789645-ce11f48c-791d-4529-abd8-18bb22646882.png)


#### - `Server` & `Client`.

```bash 
root@vm-openwrt: logread -f
Mon Apr 18 08:32:30 2022 daemon.info openwisp: Local configuration outdated
Mon Apr 18 08:32:30 2022 daemon.info openwisp: Downloading configuration from controller...
Mon Apr 18 08:32:30 2022 daemon.info openwisp: Configuration downloaded, now applying it...
Mon Apr 18 08:32:35 2022 daemon.info openwisp: OpenWISP config agent stopping
Mon Apr 18 08:32:35 2022 daemon.info openwisp: OpenWISP config agent started
Mon Apr 18 08:35:00 2022 cron.info crond[1501]: USER root pid 13119 cmd /usr/sbin/openwisp-monitoring
Mon Apr 18 08:36:00 2022 authpriv.info dropbear[13253]: Child connection from 192.168.56.1:49740
Mon Apr 18 08:36:00 2022 authpriv.notice dropbear[13253]: Pubkey auth succeeded for 'root' with key sha1!! 24:3a:1b:3f:54:66:a5:0e:3f:6a:dd:24:ea:d3:4a:b7:27:e6:f3:e2 from 192.168.56.1:49740
Mon Apr 18 08:40:00 2022 cron.info crond[1501]: USER root pid 13766 cmd /usr/sbin/openwisp-monitoring
Mon Apr 18 08:41:00 2022 authpriv.info dropbear[13910]: Child connection from 192.168.56.1:49742
Mon Apr 18 08:41:00 2022 authpriv.notice dropbear[13910]: Pubkey auth succeeded for 'root' with key sha1!! 24:3a:1b:3f:54:66:a5:0e:3f:6a:dd:24:ea:d3:4a:b7:27:e6:f3:e2 from 192.168.56.1:49742
Mon Apr 18 08:45:54 2022 authpriv.info dropbear[12428]: Exit (root): Exited normally
``` 

#### - Check if device has `active connection.`
![Screenshot from 2022-04-18 15-11-31](https://user-images.githubusercontent.com/56113566/163790778-73c382b0-5880-44b7-aeee-ae1957bca800.png)

#### - Launches `iperf3` as a client `TCP/UDP` mode.

![Screenshot from 2022-04-18 15-11-57](https://user-images.githubusercontent.com/56113566/163790783-d1dbc5d4-db23-442a-885f-a7dce7ee61f4.png)

#### - Store value '0' if server is `down/busy`.

![Screenshot from 2022-04-18 15-11-47](https://user-images.githubusercontent.com/56113566/163790782-99b28d00-117a-4387-a49f-9f5cd7081caf.png)

```python
# example 
 self.store_result({
    'iperf_result': 0,
    'sum_sent_bps': 0.0,
    'sum_rec_bps': 0.0,
     ...
     ... 
 })
```
#### - If device has `not active` connection, Skip check.


![Screenshot from 2022-04-18 15-50-36](https://user-images.githubusercontent.com/56113566/163795276-f02c07ec-370a-43e2-a676-f6c1e3c7145b.png)


#### - `Metric` & `Charts`.

```bash
>> mt.objects.all()
<QuerySet [<Metric: Ping (Device: vm-openwrt)>, <Metric: Configuration Applied (Device: vm-openwrt)>, <Metric: eth1 traffic (Device: vm-openwrt)>, <Metric: CPU usage (Device: vm-openwrt)>, <Metric: Disk usage (Device: vm-openwrt)>, <Metric: Memory usage (Device: vm-openwrt)>, <Metric: Iperf (Device: vm-openwrt)>]>
# <Metric: Iperf (Device: vm-openwrt)> 'name': 'Iperf', 'key': 'iperf', 'field_name': 'iperf_result', 'configuration': 'iperf'

>>> ch.objects.all()
<QuerySet [<Chart: Uptime>, <Chart: Packet loss>, <Chart: Round Trip Time>, <Chart: Traffic>, <Chart: CPU Load>, <Chart: Disk Usage>, <Chart: Memory Usage>, <Chart: Bits per second>, <Chart: Transfer>, <Chart: Retransmits>]>
# <Chart: Bits per second> 'configuration': 'bps', <Chart: Transfer> 'configuration': 'transfer', Chart: Retransmits> 'configuration': 'retransmits'
```

#### - Server `iperf result`.

![Screenshot from 2022-04-16 13-12-47](https://user-images.githubusercontent.com/56113566/163666812-8db6fe63-9398-4f60-a287-5fbe78ea441f.png)


![-------------------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)