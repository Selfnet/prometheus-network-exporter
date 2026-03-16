from pygnmi.client import gNMIclient
from getpass import getpass

# Variables
host = ("100.127.6.13", "57400")

# Body
if __name__ == "__main__":
    with gNMIclient(
        target=host,
        username="marcelf",
        password=getpass("You password please?:"),
        insecure=True,
    ) as gc:
        result = gc.get(path=["openconfig-interfaces:interfaces", "openconfig-acl:acl"])
    print(result)
