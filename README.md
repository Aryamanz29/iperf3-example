# Add iperf bandwidth monitoring check to OpenWISP Monitoring


- The goal of this project is to **add a bandwidth test using iperf3**, using the **active check mechanism** of **OpenWISP Monitoring.**

- The use case is to perform periodic bandwidth test to measure the max     bandwidth available **(TCP test)** and **jitter (UDP)**.

- On a macro level, the check would work this way:

    - OpenWISP connects to the device (only 1 check per device at time) via **SSH** and launches **iperf3** as a **client**, first in **TCP mode**, then in **UDP mode**, **iperf** is launched with the **-j flag** to obtain **json output**

- The collected data is parsed and stored as a **metric (bandwidth information and jitter)**

- **SSH** connection is closed

## Expected outcomes

The outcomes we expect from this project are the following:

- Create **iperf check class**, the check must use the connection module of openwisp-controller to connect to devices using SSH

- If a device has **no active Connection** the check will be **skipped** and a **warning logged.**

- This check should be **optional** and **disabled by default**

- We can run it by **default every night**

- Allow **configuring the iperf server** globally and by organization with a setting, eg:

```python
OPENWISP_MONITORING_IPERF_SERVERS = {
    '': ['<DEFAULT_IPERF_SERVER_HERE>'],
    '<org-pk>': ['<ORG_IPERF_SERVER>']
}
```
- It shall be possible to specify a **list of iperf servers**, this is important because on larger systems **1 server will not be enough.**

- We have to **implement a lock to allow** only **1 iperf check per server at time** that is: for every server available, only **1 check can be performed at any one time**, so the lock has to take this account when **calculating the cache-key**

- **SSH into device**, launch **iperf TCP client**, **repeat for UDP**, **collect data** of both tests in a **data structure**

- **Handle failures**, **if server is down**, we can **store 0**, which would **trigger an alert** (investigate the alert settings functionality)

- Implement logic which **creates the metric, chart and alert settings objects**

- Save data (tcp max bandwidth, UDP jitter)

- Document how this check works

- Document how to set up and use the check step by step (explain also how to set up a new iperf server)

- Achieve at least **99% test coverage** for the code added for this feature.

