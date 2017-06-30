#!/usr/bin/python
import json
from multiprocessing import Process, Queue, Manager, current_process, freeze_support
import threading
import time
import xmlrpc.client
import http.client

import processespool
from strategyAgent import StdStrategy, SpecialStrategy

SUCCESS = True
FAILED = False
NUM_OF_READ_PROCESSES = 100
NUM_OF_SET_PROCESSES = NUM_OF_READ_PROCESSES / 2 if NUM_OF_READ_PROCESSES / 2 < 1 else 1


class TimeoutTransport(xmlrpc.client.Transport):
    def set_timeout(self, timeout):
        self.timeout = timeout

    def make_connection(self, host):
        hconn = http.client.HTTPConnection(host, timeout=self.timeout)
        return hconn


class LeafNode(object):
    def __init__(self, uuid, name, minimal_power, priority_group, physical_info, task_info, ip='0.0.0.0',
                 rpc_port='5001', bmc_ip='0.0.0.0'):
        self.uuid = uuid
        self.name = name
        self.minimal_power = minimal_power
        self.priority_group = priority_group
        self.physical_info = physical_info  # string
        self.task_info = task_info  # string
        self.ip = ip
        self.rpc_port = rpc_port
        self.bmc_ip = bmc_ip
        self.cur_power = 0
        self.peak_power = self.minimal_power
        self.connectivity_error = False
        self.connectivity_error_cnt = 0
        self.power_limit = 0

    def clr_connectivity_error(self):
        self.connectivity_error = False
        self.connectivity_error_cnt = 0

    def inc_connectivity_error_cnt(self):
        self.connectivity_error_cnt += 1
        if self.connectivity_error_cnt > 2:
            self.connectivity_error_cnt = 3
            self.connectivity_error = True


def proxy_read_node_power(uuid, rpc_ip, rpc_port):
    return LeafController.read_node_power(uuid, rpc_ip, rpc_port)


def proxy_set_node_powerlimit(uuid, rpc_ip, rpc_port, power_limit):
    return LeafController.set_node_powerlimit(uuid, rpc_ip, rpc_port, power_limit)


class LeafController(object):
    def __init__(self, uuid, name, minimal_power, physical_power_limit, proc_pool, strategy_class=StdStrategy,
                 ip='0.0.0.0', rpc_port='5001'):
        self.uuid = uuid
        self.name = name
        self.minimal_power = minimal_power
        self.physical_power_limit = physical_power_limit
        self.cur_power = 0
        self.nodes_power_sum = 0
        self.contractual_power_limit = 0
        self.ip = ip
        self.rpc_port = rpc_port
        self.leaf_node_list = {}
        self.leaf_node_list_0 = {}
        self.leaf_node_list_1 = {}
        self.leaf_node_list_2 = {}
        self.leaf_node_list_3 = {}
        self.proc_pool = proc_pool
        self.node_list_lock = threading.Lock()
        self.strategy = strategy_class()

    def add_node(self, uuid, leafnode):
        self.leaf_node_list.setdefault(uuid, leafnode)
        if 0 == leafnode.priority_group:
            self.leaf_node_list_0.setdefault(uuid, leafnode)
            return
        if 1 == leafnode.priority_group:
            self.leaf_node_list_1.setdefault(uuid, leafnode)
            return
        if 2 == leafnode.priority_group:
            self.leaf_node_list_2.setdefault(uuid, leafnode)
            return
        if 3 == leafnode.priority_group:
            self.leaf_node_list_3.setdefault(uuid, leafnode)
            return

    # compose leaf nodes from json configure file.
    def compose_nodes(self):
        with open("conf/nodes.json") as cfg_file:
            cfg_data = json.load(cfg_file)
        for key in cfg_data.keys():
            node_info = cfg_data[key]
            leafnode = LeafNode(node_info["uuid"], node_info["name"], int(node_info["minimal_power"]),
                                int(node_info["priority_group"]), node_info["physical_info"], node_info["task_info"],
                                node_info["ip"], node_info["rpc_port"], node_info["bmc_ip"])
            self.add_node(leafnode.uuid, leafnode)
        return

    def show_nodes(self):
        with self.node_list_lock:
            for uuid in self.leaf_node_list:
                name = self.leaf_node_list[uuid].name
                cur_power = self.leaf_node_list[uuid].cur_power
                print("%10s current power is %6dw" % (name, cur_power))
            return

    @staticmethod
    def read_node_power(uuid, rpc_ip, rpc_port):
        status = SUCCESS
        power = 0
        timeout_transport = TimeoutTransport()
        timeout_transport.set_timeout(1.0)
        leafnode_rcp_if = xmlrpc.client.ServerProxy("http://%s:%s" % (rpc_ip, rpc_port), transport=timeout_transport)
        try:
            read_status, power = leafnode_rcp_if.read_power()
        except Exception as expt:
            status = FAILED
            read_status = expt
        return status, read_status, uuid, power

    @staticmethod
    def set_node_powerlimit(uuid, rpc_ip, rpc_port, power_limit):
        status = SUCCESS
        leafnode_rcp_if = xmlrpc.client.ServerProxy("http://%s:%s" % (rpc_ip, rpc_port))
        try:
            set_status = leafnode_rcp_if.set_power_limit(power_limit)
        except Exception as expt:
            status = FAILED
            set_status = expt
        return status, set_status, uuid

    def pull_nodes_power(self):
        print("pulling nodes power ==>")
        with self.node_list_lock:
            for uuid in self.leaf_node_list.keys():
                ip = self.leaf_node_list[uuid].ip;
                rpc_port = self.leaf_node_list[uuid].rpc_port
                task = (proxy_read_node_power, (uuid, ip, rpc_port))
                self.proc_pool.put_read_node_work(task)
        # time.sleep(1)
        with self.node_list_lock:
            for i in range(len(self.leaf_node_list)):
                status, read_status, uuid, power = self.proc_pool.get_read_node_work()
                node = self.leaf_node_list[uuid]
                if status is SUCCESS and read_status is SUCCESS:
                    node.cur_power = power
                    node.peak_power = power if power > node.peak_power else node.peak_power
                    node.clr_connectivity_error()
                    print("read %s --> %d" % (uuid, power))
                else:
                    node.inc_connectivity_error_cnt()
                    print("read %s --> %s" % (uuid, read_status))

    def estimate_nodes_power(self):
        # for those node who is suffering a network error, and whose BMC is unaccessible either.
        self.strategy.estimate_nodes_power(self)

    def aggregate_nodes_power(self):
        self.strategy.aggregate_nodes_power(self)

    def update_cur_power(self):
        self.strategy.update_cur_power(self)

    def run(self):
        i = 1
        std_strategy = StdStrategy()
        specical_strategy = SpecialStrategy()
        while True:
            self.pull_nodes_power()
            self.estimate_nodes_power()
            self.show_nodes()
            self.aggregate_nodes_power()
            self.update_cur_power()
            time.sleep(3)
            # below code for test only
            i += 1
            if i % 2:
                self.strategy = std_strategy
            else:
                self.strategy = specical_strategy


if __name__ == "__main__":
    proc_pool = processespool.ProcPool(NUM_OF_READ_PROCESSES, NUM_OF_SET_PROCESSES)
    leaf_controller = LeafController("leafc0", "leafc0", 1000, 9000, proc_pool, StdStrategy, "10.1.1.2")
    leaf_controller.compose_nodes()
    leaf_controller.show_nodes()
    leaf_controller.run()
