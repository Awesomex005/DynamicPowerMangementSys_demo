#!/usr/bin/python
import json


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


class LeafController(object):
    def __init__(self, uuid, name, minimal_power, physical_power_limit, ip='0.0.0.0', rpc_port='5001'):
        self.uuid = uuid
        self.name = name
        self.minimal_power = minimal_power
        self.physical_power_limit = physical_power_limit
        self.ip = ip
        self.rpc_port = rpc_port
        self.leaf_node_list_0 = {}
        self.leaf_node_list_1 = {}
        self.leaf_node_list_2 = {}
        self.leaf_node_list_3 = {}

    def add_node(self, uuid, leafnode):
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
            leafnode = LeafNode(node_info["uuid"], node_info["name"], node_info["minimal_power"],
                                int(node_info["priority_group"]), node_info["physical_info"], node_info["task_info"],
                                node_info["ip"], node_info["rpc_port"], node_info["bmc_ip"])
            self.add_node(leafnode.uuid, leafnode)
        return

    def show_nodes(self):
        print"priority_group 0: ",
        print(self.leaf_node_list_0)
        print"priority_group 1: ",
        print(self.leaf_node_list_1)
        print"priority_group 2: ",
        print(self.leaf_node_list_2)
        print"priority_group 3: ",
        print(self.leaf_node_list_3)
        return


if __name__ == "__main__":
    leaf_controller = LeafController("leafc0", "leafc0", 1000, 9000, "10.1.1.2")
    leaf_controller.compose_nodes()
    leaf_controller.show_nodes()
