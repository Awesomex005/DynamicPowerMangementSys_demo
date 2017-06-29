#!/usr/bin/python
import json
from SimpleXMLRPCServer import SimpleXMLRPCServer
import threading

'''
    This module should be a agent runs on a leafnode device.
'''

SUCCESS = True
FAILED = False


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
        self.rpc_port = int(rpc_port)
        self.bmc_ip = bmc_ip
        self.cur_power = 0


class LeafNodeAgent(object):
    def __init__(self, leafnode):
        self.leafnode = leafnode
        self.rpc_server = SimpleXMLRPCServer((self.leafnode.ip, self.leafnode.rpc_port), logRequests=False)

    def read_power(self):
        # TODO
        sys_power = 300
        print("%s current power: %d" % (self.leafnode.name, sys_power))
        return SUCCESS, sys_power

    def set_power_limit(self, power_limit):
        # TODO
        print("Set %s power limit to: %d" % (self.leafnode.name, power_limit))
        return SUCCESS


if __name__ == "__main__":
    with open("conf/leafnode.json") as cfg_file:
        node_info = json.load(cfg_file)
    leafnode = LeafNode(node_info["uuid"], node_info["name"], node_info["minimal_power"],
                        int(node_info["priority_group"]), node_info["physical_info"], node_info["task_info"],
                        node_info["ip"], node_info["rpc_port"], node_info["bmc_ip"])
    leafnode_agent = LeafNodeAgent(leafnode)
    leafnode_agent.rpc_server.register_instance(leafnode_agent)
    rpc_server = threading.Thread(target=leafnode_agent.rpc_server.serve_forever)
    try:
        rpc_server.start()
    except KeyboardInterrupt as excpt:
        print(excpt)
        exit()
    except Exception as excpt:
        print(excpt)
        exit()
