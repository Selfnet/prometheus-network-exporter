# junos_prometheus_exporter

## Install requirements

```bash

    pip install -r requirements.txt -U

```

## Run program

```bash
    python main.py
```

## Query for junos_devices

    http://localhost:8000/metric?hostname=device.example.com&access=False&hostname=device2.example.com&access=True

## Look for prometheus config

Example config for your prometheus can be found under `prometheus/*`
