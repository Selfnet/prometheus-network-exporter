import linecache
import os
import tracemalloc

import tornado


class TraceMallocHandler(tornado.web.RequestHandler):
    def display_top(self, snapshot, key_type="lineno", limit=10):
        self.set_status(200, "Ok")
        self.set_header("Content-type", "text/plain")
        snapshot = snapshot.filter_traces(
            (
                tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
                tracemalloc.Filter(False, "<unknown>"),
            )
        )
        top_stats = snapshot.statistics(key_type)

        self.write(bytes(f"Top {limit} lines\n".encode("utf-8")))
        for index, stat in enumerate(top_stats[:limit], 1):
            frame = stat.traceback[0]
            # replace "/path/to/module/file.py" with "module/file.py"
            filename = os.sep.join(frame.filename.split(os.sep)[-2:])
            self.write(
                bytes(
                    (
                        "#%s: %s:%s: %.1f KiB\n"
                        % (index, filename, frame.lineno, stat.size / 1024)
                    ).encode("utf-8")
                )
            )
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                self.write(f"    {line}\n")

        other = top_stats[limit:]
        if other:
            size = sum(stat.size for stat in other)
            self.write(
                bytes(
                    ("%s other: %.1f KiB\n" % (len(other), size / 1024)).encode("utf-8")
                )
            )
        total = sum(stat.size for stat in top_stats)
        self.write(
            bytes(("Total allocated size: %.1f KiB\n" % (total / 1024)).encode("utf-8"))
        )

    async def get(self):
        if not self.application.debug:
            raise tornado.web.HTTPError(404)
        key_type = str(self.get_argument("key_type", "lineno"))
        assert key_type in ["lineno", "traceback"]
        limit = int(self.get_argument("limit", 20))
        self.display_top(tracemalloc.take_snapshot(), key_type=key_type, limit=limit)
