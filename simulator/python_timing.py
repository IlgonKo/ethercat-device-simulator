"""Optional local-only timing: elapsed time and current thread CPU time."""
import json
import time


def stamp():
    return time.perf_counter_ns(), time.thread_time_ns()


class PythonTiming:
    def __init__(self, axes):
        self.axes = axes
        self.start = self.last = time.perf_counter_ns()
        self.metrics = {}

    def add(self, key, begin, end):
        wall = (end[0] - begin[0]) / 1e6
        cpu = (end[1] - begin[1]) / 1e6
        b = self.metrics.setdefault(key, dict(count=0, total_ms=0, cpu_total_ms=0,
            min_ms=wall, max_ms=wall, cpu_max_ms=cpu))
        b['count'] += 1; b['total_ms'] += wall; b['cpu_total_ms'] += cpu
        b['min_ms'] = min(b['min_ms'], wall); b['max_ms'] = max(b['max_ms'], wall)
        b['cpu_max_ms'] = max(b['cpu_max_ms'], cpu)

    def due(self):
        if time.perf_counter_ns() - self.last >= 1_000_000_000:
            self.flush('interval')

    def flush(self, reason):
        if not self.metrics: return
        begin = stamp()
        metrics, self.metrics = self.metrics, {}
        for b in metrics.values():
            b['avg_ms'] = b.pop('total_ms') / b['count']
            b['cpu_avg_ms'] = b.pop('cpu_total_ms') / b['count']
        print(json.dumps(dict(event='python-timing', reason=reason, axes=self.axes,
            unix_ms=time.time_ns()/1e6, elapsed_s=(begin[0]-self.start)/1e9,
            window_s=(begin[0]-self.last)/1e9, metrics=metrics), separators=(',', ':')), flush=True)
        self.last = begin[0]
        self.add('timing_log', begin, stamp())
