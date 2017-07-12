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
    def init_param(self, tgt=0.95, upper_threshold=0.99, lower_threshold=0.90):
        self.tgt = tgt
        self.upper_threshold = upper_threshold
        self.lower_threshold = lower_threshold

    def compose_nodes(self, lc_obj, leafnode_cls):
        # compose leaf nodes from json configure file.
        with open("conf/nodes.json") as cfg_file:
            cfg_data = json.load(cfg_file)
        for key in cfg_data.keys():
            node_info = cfg_data[key]
            leafnode = leafnode_cls(node_info["uuid"], node_info["name"], int(node_info["minimal_power"]),
                                    int(node_info["priority_group"]), node_info["physical_info"],
                                    node_info["task_info"],
                                    node_info["ip"], node_info["rpc_port"], node_info["bmc_ip"])
            lc_obj.add_node(leafnode.uuid, leafnode)
        return

    def rt_add_node(self, lc_obj, node_info):
        # adding node during run time.
        # this function should be invoked before the new server node being physically inserted to the power delivery hierarchy.
        leafnode = leafnode_cls(node_info["uuid"], node_info["name"], int(node_info["minimal_power"]),
                                int(node_info["priority_group"]), node_info["physical_info"], node_info["task_info"],
                                node_info["ip"], node_info["rpc_port"], node_info["bmc_ip"])
        lc_obj.add_node(leafnode.uuid, leafnode)

    def estimate_nodes_power(self, lc_obj):
        with lc_obj.node_list_lock:
            for uuid in lc_obj.leaf_node_list.keys():
                node = lc_obj.leaf_node_list[uuid]
                if node.connectivity_error:
                    # TODO estimate node power according to peer nodes.
                    pass
                    # failed to estimate node power according to peer nodes, use its peak_power
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

    def uncap_leafnodes(self, lc_obj):
        with lc_obj.node_list_lock:
            for uuid in lc_obj.leaf_node_list.keys():
                leafnode = lc_obj.leaf_node_list[uuid]
                leafnode.power_limit = 0

    def power_limit_decision(self, lc_obj):
        print("make power capping decision ==>")
        with lc_obj.ctrl_lock:
            if lc_obj.contractual_power_limit:
                power_limit = lc_obj.contractual_power_limit
            else:
                power_limit = lc_obj.physical_power_limit

            if lc_obj.cur_power >= power_limit * self.upper_threshold:
                print("[cap]")
                total_power_cut = lc_obj.cur_power - power_limit * self.tgt
                with lc_obj.node_list_lock:
                    lfnode_3_ascending = sorted(lc_obj.leaf_node_list_3.items(), key=lambda lfnode: lfnode[1].cur_power,
                                                reverse=True)
                    lfnode_2_ascending = sorted(lc_obj.leaf_node_list_2.items(), key=lambda lfnode: lfnode[1].cur_power,
                                                reverse=True)
                    lfnode_1_ascending = sorted(lc_obj.leaf_node_list_1.items(), key=lambda lfnode: lfnode[1].cur_power,
                                                reverse=True)
                    lfnode_0_ascending = sorted(lc_obj.leaf_node_list_0.items(), key=lambda lfnode: lfnode[1].cur_power,
                                                reverse=True)
                    lfnode_in_order =[]
                    lfnode_in_order.append(lfnode_3_ascending); lfnode_in_order.append(lfnode_2_ascending)
                    lfnode_in_order.append(lfnode_1_ascending); lfnode_in_order.append(lfnode_0_ascending)
                    for lfnode_group in lfnode_in_order:
                        for item in lfnode_group:
                            lfnode = item[1]
                            power_cut = min(lfnode.cur_power - lfnode.minimal_power, total_power_cut)
                            lfnode.power_limit = lfnode.cur_power - power_cut
                            total_power_cut -= power_cut
                            if not total_power_cut:
                                break
                        if not total_power_cut:
                            break
            elif lc_obj.cur_power <= power_limit * self.lower_threshold:
                print("[uncap]")
                self.uncap_leafnodes(lc_obj)


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
