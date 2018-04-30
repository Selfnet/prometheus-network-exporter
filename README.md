# prometheus_junos_exporter

## Install Requirements

```bash
    pip install .
```

## The Exporter

### Configuration

The configuration is under `/etc/prometheus-junos-exporter/config.yml` you should change the configuration.
No configuration means, that the current logged in user is used and its configuration.
The SSH config is also used.
#### example

```bash
    gunicorn prometheus_junos_exporter.app:app -b 127.0.0.1:9332 --name prometheus-junos-exporter --log-level=info --log-file=- -w 12 --max-requests 40 -k eventlet
```

## HowTo: Query for junos_devices

    http://localhost:9332/metrics?target=device.example.com&module=default

If access is True only the interfaces for the ports specified in
`config/metrics_definitions.yml` are queried and if access is False everything is queried.
The default definition for access=True is:

```yml
NETWORK_REGEXES:
    - ge-*/1/*
    - xe-*/*/*
```

Those are backbone ports on our access switches. So access defines if it is a backbone switch/router or a access switch.

## Look for prometheus config

Example config for your prometheus can be found under `prometheus/*`.

## For Enthusiasts

You can also configure the metrics definitions.
If their are not enough Metrics.
Configure `config/metrics_definitions.yml` and add functions to junos_exporter if the ouput is non trivial.

At the moment only Interfaces, environment and bgp Metrics are supported.
So only the Metrics Counter and Gauge are implemented.
Feel free to add Pull Requests to extend the implementation.