import traceback
from queue import Queue
from threading import Lock, Thread

import sys


class MyWorkers:

    def __init__(self, workers_num):
        self._queue = Queue()
        self.workers_num = workers_num
        self.threads = []
        self.tasks = set()
        self.run_workers()
        self.lock = Lock()

    def worker(self):
        while True:
            item = self._queue.get()

            if item is None:
                print('worker break')
                break

            func, args, name = item
            counter = 0
            self.tasks.add(name)
            # while counter < 3:
            #     counter += 1
            try:
                func(*args)
                # break
            except Exception as err:
                with self.lock:
                    print('Ошибка в myworkers', counter, func, args, str(err))
                traceback.print_exc(file=sys.stdout)

            self._queue.task_done()

            if name in self.tasks:
                self.tasks.remove(name)
        print('worker off')

    def kill_worker(self):
        self._queue.put(None)

    def add_worker(self):
        t = Thread(target=self.worker, daemon=True)
        t.start()
        self.threads.append(t)

    def run_workers(self):
        for _ in range(self.workers_num):
            self.add_worker()

    def add_task(self, func, args=(), name=''):
        self._queue.put((func, args, name))
