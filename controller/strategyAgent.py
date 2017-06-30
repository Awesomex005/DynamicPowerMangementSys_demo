#!/usr/bin/python
import json
from multiprocessing import Process, Queue, Manager, current_process, freeze_support
import threading
import time
import xmlrpc.client
import http.client

import processespool

SUCCESS = True
FAILED = False


class StdStrategy(object):
    def estimate_nodes_power(self, lc_obj):
        with lc_obj.node_list_lock:
            for uuid in lc_obj.leaf_node_list.keys():
                node = lc_obj.leaf_node_list[uuid]
                if node.connectivity_error:
                    # TODO estimate node power according to peer nodes.
                    pass
                    # failed to estimate node power according to peer nodes
                    lc_obj.leaf_node_list[uuid].cur_power = lc_obj.leaf_node_list[uuid].peak_power

    def aggregate_nodes_power(self, lc_obj):
        power_aggregation = 0
        with lc_obj.node_list_lock:
            for uuid in lc_obj.leaf_node_list.keys():
                power_aggregation += lc_obj.leaf_node_list[uuid].cur_power
        lc_obj.nodes_power_sum = power_aggregation
        print("Power Aggregation : %6dw" % power_aggregation)
        return power_aggregation

    def update_cur_power(self, lc_obj):
        lc_obj.cur_power = lc_obj.nodes_power_sum
        print("Leaf Controller Current Power : %6dw" % lc_obj.cur_power)


class SpecialStrategy(StdStrategy):
    def estimate_nodes_power(self, lc_obj):
        with lc_obj.node_list_lock:
            for uuid in lc_obj.leaf_node_list.keys():
                node = lc_obj.leaf_node_list[uuid]
                if node.connectivity_error:
                    # TODO read node power via its BMC
                    pass
                    # TODO estimate node power according to peer nodes.
                    pass
                    # when failed to estimate node power according to peer nodes
                    lc_obj.leaf_node_list[uuid].cur_power = lc_obj.leaf_node_list[uuid].peak_power

    def update_cur_power(self, lc_obj):
        # TODO read leaf controller power from a real physical sensor
        lc_obj.cur_power = lc_obj.nodes_power_sum
        print("special strategy updating current leaf controller power.")
        print("Leaf Controller Current Power : %6dw" % lc_obj.cur_power)
