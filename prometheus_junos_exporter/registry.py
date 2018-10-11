

class Metrics(object):
    """
    Store metrics and do conversions to PromQL syntax
    """

    class _Metric(object):
        """
        This is an actual metric entity
        """

        def __init__(self, name, value, metric_type, labels=None):
            self.name = name
            self.value = float(value)
            self.metric_type = metric_type
            self.labels = []
            if labels:
                for label_name, label_value in labels.items():
                    self.labels.append(
                        '{}="{}"'.format(label_name, label_value))

        def __str__(self):
            return "{}{} {}".format(self.name, "{" + ",".join(self.labels) + "}", self.value)

    def __init__(self):
        self._metrics_registry = {}
        self._metric_types = {}
        self._metrics_description = {}

    def register(self, name, description, metric_type):
        """
        Add a metric to the registry
        """
        if self._metrics_registry.get(name) is None:
            self._metrics_registry[name] = []
            self._metric_types[name] = metric_type
            self._metrics_description[name] = description
        else:
            raise ValueError(
                'Metric named {} is already registered.'.format(name))

    def add_metric(self, name, value, labels=None):
        """
        Add a new metric
        """
        collector = self._metrics_registry.get(name)
        if collector is None:
            raise ValueError('Metric named {} is not registered.'.format(name))

        metric = self._Metric(name, value, self._metric_types[name], labels)
        collector.append(metric)

    def collect(self):
        """
        Collect all metrics and return
        """
        lines = []
        for name, metric_type in self._metric_types.items():
            lines.append("# HELP {} {}".format(
                name, self._metrics_description[name]))
            lines.append("# TYPE {} {}".format(name, metric_type))
            lines.extend(self._metrics_registry[name])
        return "\n".join([str(x) for x in lines]) + '\n'
