"""
Allocate a cluster of CloudLab machines for RAMCloud.
"""

import geni.urn as urn
import geni.portal as portal
import geni.rspec.pg as rspec
import geni.aggregate.cloudlab as cloudlab

# The possible set of base disk-images that this cluster can be booted with.
# The second field of every tupule is what is displayed on the cloudlab
# dashboard.
images = [ ("UBUNTU14-64-STD", "Ubuntu 14.04 (64-bit)"),
        ("UBUNTU15-04-64-STD", "Ubuntu 15.04 (64-bit)"),
        ("UBUNTU16-64-STD", "Ubuntu 16.04 (64-bit)") ]

# The possible set of node-types this cluster can be configured with.
nodes = [ ("r320", "r320 (Xeon E5 2450, 16 GB RAM, 56 Gbps Mellanox VPI)"),
        ("c6220", "c6220 (2 x Xeon E5 2650v2, 64 GB RAM, 56 Gbps Mellanox VPI")
        ]

# The set of disks on which RAMCloud will store segment replicas.
disks = [ "/dev/sdb", "/dev/sdc" ]

# Allows for general parameters like disk image to be passed in. Useful for
# setting up the cloudlab dashboard for this profile.
context = portal.Context()

# Default the disk image to 64-bit Ubuntu 15.04
context.defineParameter("image", "Disk Image",
        portal.ParameterType.IMAGE, images[1], images,
        "Specify the base disk image that all the nodes of the cluster " +\
        "should be booted with.")

# Default the node type to the c6220.
context.defineParameter("type", "Node Type",
        portal.ParameterType.NODETYPE, nodes[1], nodes,
        "Specify the type of nodes the cluster should be configured with. " +\
        "For more details, refer to " +\
        "\"http://docs.cloudlab.us/hardware.html#%28part._apt-cluster%29\"")

# Default the cluster size to 8 nodes.
context.defineParameter("size", "Cluster Size",
        portal.ParameterType.INTEGER, 8, [],
        "Specify the size of the cluster. Please make sure there are two " +\
        "additional nodes; one for management (rcmaster), and one for " +\
        "nfs (rcnfs). To check availability of nodes, visit " +\
        "\"https://www.cloudlab.us/cluster-graphs.php\"")

params = context.bindParameters()

# Reject requests for clusters smaller than 8 nodes.
if params.size < 8:
    context.reportError(portal.ParameterError(
            "The cluster must consist of atleast 8 nodes."))

request = rspec.Request()

# Create a local area network.
lan = rspec.LAN()
request.addResource(lan)

# Setup node names so that existing RAMCloud scripts can be used on the
# cluster.
rc_aliases = ["rcmaster", "rcnfs"]
for i in range(params.size - 2):
    rc_aliases.append("rc%02d" % (i + 1))

# Setup the cluster one node at a time.
for i in range(params.size):
    node = rspec.RawPC(rc_aliases[i])

    node.hardware_type = params.type
    node.disk_image = urn.Image(cloudlab.Utah, "emulab-ops:%s" % params.image)

    # Request for a 200GB filesystem on the nfs server (rcnfs).
    if rc_aliases[i] == "rcnfs":
        bs = node.Blockstore("bs", "/shome")
        bs.size = "200GB"

    # Install and run the startup scripts.
    node.addService(rspec.Install(
            url="https://github.com/chinkulkarni/RAMCloud-CloudLab-Scripts/" +\
                    "archive/master.tar.gz",
            path="/local"))
    node.addService(rspec.Execute(
            shell="sh", command="sudo mv /local/RAMCloud-CloudLab-Scripts-master " +\
                    "/local/scripts"))
    node.addService(rspec.Execute(
            shell="sh",
            command="sudo /local/scripts/startup.sh %d" % params.size))

    # Set disk permissions on all nodes except rcmaster and rcnfs.
    if rc_aliases[i] != "rcmaster" and rc_aliases[i] != "rcnfs":
        for disk in disks:
            node.addService(rspec.Execute(
                    shell="sh", command="sudo chmod 777 %s" % disk))

    request.addResource(node)

    # Add this node to the LAN.
    iface = node.addInterface("eth0")
    lan.addInterface(iface)

# Generate the RSpec
context.printRequestRSpec(request)
