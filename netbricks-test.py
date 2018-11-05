"""
Allocate a cluster of CloudLab machines to test NetBricks.

Instructions:
"""

import geni.urn as urn
import geni.portal as portal
import geni.rspec.pg as rspec
import geni.aggregate.cloudlab as cloudlab

# The possible set of base disk-images that this cluster can be booted with.
# The second field of every tupule is what is displayed on the cloudlab
# dashboard.
images = [ ("UBUNTU16-64-STD", "Ubuntu 16.04 (64-bit)") ]

# The possible set of node-types this cluster can be configured with.
nodes = [
        ("d430", "d430 (2 x Xeon E5 2630v3, 64 GB RAM, 10 Gbps Intel Ethernet)")
        ]

# The set of disks to mount.
disks = [ "/dev/sdb", "/dev/sdc" ]

# Allows for general parameters like disk image to be passed in. Useful for
# setting up the cloudlab dashboard for this profile.
context = portal.Context()

# Default the disk image to 64-bit Ubuntu 16.04
context.defineParameter("image", "Disk Image",
        portal.ParameterType.IMAGE, images[0], images,
        "Specify the base disk image that all the nodes of the cluster " +\
        "should be booted with.")

# Default the node type to the d430.
context.defineParameter("type", "Node Type",
        portal.ParameterType.NODETYPE, nodes[0], nodes,
        "Specify the type of nodes the cluster should be configured with. " +\
        "For more details, refer to " +\
        "\"http://docs.cloudlab.us/hardware.html#%28part._apt-cluster%29\"")

# Default the cluster size to 2 nodes.
context.defineParameter("size", "Cluster Size",
        portal.ParameterType.INTEGER, 2, [],
        "Specify the size of the cluster." +\
        "To check availability of nodes, visit " +\
        "\"https://www.cloudlab.us/cluster-graphs.php\"")

params = context.bindParameters()

request = rspec.Request()

# Create a local area network over a 10 Gbps.
lan = rspec.LAN()
lan.bandwidth = 10000000 # This is in kbps.

# Setup node names.
rc_aliases = []
for i in range(params.size):
    rc_aliases.append("netbricks%02d" % (i + 1))

# Setup the cluster one node at a time.
for i in range(params.size):
    node = rspec.RawPC(rc_aliases[i])

    node.hardware_type = params.type
    node.disk_image = urn.Image(cloudlab.Utah, "emulab-ops:%s" % params.image)
    node.Site('Site 1')

    # Install and run the startup scripts.
    node.addService(rspec.Install(
            url="https://github.com/chinkulkarni/cloudLab-scripts/" +\
                    "archive/master.tar.gz",
            path="/local"))
    node.addService(rspec.Execute(
            shell="sh", command="sudo mv /local/cloudLab-scripts-master " +\
                    "/local/scripts"))

    node.addService(rspec.Execute(
            shell="sh",
            command="sudo /local/scripts/netbricks_setup.sh"))

    request.addResource(node)

    # Add this node to the LAN.
    iface = node.addInterface("eth0")
    lan.addInterface(iface)

# Add the lan to the request.
request.addResource(lan)

# Generate the RSpec
context.printRequestRSpec(request)
