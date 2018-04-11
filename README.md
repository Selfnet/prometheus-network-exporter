# prometheus_junos_exporter

## Install Requirements

```bash
    pip install .
```

## The Exporter

### Configuration

In the `config/` folder rename `config-sample.yml` to `config.yml` and specify `USERNAME` if it is not your system user
and a keyfile.
If you are not using a SSH Priv Keyfile. You are been asked by the program for a SSH user password.

### Run the program

```bash
    pyez-exporter --version
```

defaults to [http://localhost:8000](http://localhost:8000)
you can specify addr and port on the cli.

#### example

```bash
    pyez-exporter --port 9000
    pyez-exporter --
```

## HowTo: Query for junos_devices

    http://localhost:8000/metric?hostname=device.example.com&access=False&hostname=device2.example.com&access=True

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

Example config for your prometheus can be found under `prometheus/*`

## For Enthusiasts

You can also configure the metrics definitions.
If their are not enough Metrics.
Configure `config/metrics_definitions.yml` and add functions to junos_exporter if the ouput is non trivial.

At the moment only Interfaces and environment Metrics are support.
So only Counter and Gauge are implemented.
Feel free to add Pull Requests to extend the implementation.