from multiprocessing import Process, Queue, Manager, current_process, freeze_support
import time


class ControllerProcessesPool(object):
    def __init__(self, read_node_q, read_node_done_q, set_node_q, set_node_done_q, num_of_read_proc, num_of_set_proc):
        self.read_node_q = read_node_q
        self.read_node_done_q = read_node_done_q
        self.set_node_q = set_node_q
        self.set_node_done_q = set_node_done_q
        self.num_of_read_proc = num_of_read_proc
        self.num_of_set_proc = num_of_set_proc

    def worker(self, input_q, output_q):
        for func, args in iter(input_q.get, 'STOP'):
            result = self.do_work(func, args)
            output_q.put(result)

    def do_work(self, func, args):
        result = func(*args)
        print ('ProcPool: %s says that %s%s = %s' %
               (current_process().name, func.__name__, args, result))
        return result

    def put_read_node_work(self, task):
        self.read_node_q.put(task)

    def put_set_node_work(self, task):
        self.set_node_q.put(task)

    def get_read_node_work(self):
        return self.read_node_done_q.get()

    def get_set_node_work(self):
        return self.set_node_done_q.get()

    def start(self):
        for i in range(self.num_of_read_proc):
            Process(target=self.worker, args=(self.read_node_q, self.read_node_done_q)).start()
        for i in range(self.num_of_set_proc):
            Process(target=self.worker, args=(self.set_node_q, self.set_node_done_q)).start()


# this func should be called immediately after "if __name__ == '__main__':".
def ProcPool(num_of_read_processes, num_of_set_processes):
    freeze_support()
    read_node_q = Queue()
    read_node_done_q = Queue()
    set_node_q = Queue()
    set_node_done_q = Queue()
    proc_pool = ControllerProcessesPool(read_node_q, read_node_done_q, set_node_q, set_node_done_q,
                                        num_of_read_processes, num_of_set_processes)
    proc_pool.start()
    return proc_pool
