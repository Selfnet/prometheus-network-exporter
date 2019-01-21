# The problem of MultiVendor YANG

With the current solution I have support for Juniper Switches.
To extend this support a new architecture should be designed using 
off the shelve packages which work on most of the devices.

This is the introduction of the plain *ncclient*. Without vendor specific settings. (e.g. pyez and ydk-py).

Most of the new Software Releases are capable of using the IETF YANG standard.
But all of them are brewing their own client implementation as mentioned above.
To consolidate this my aproach is to use the vendor specific YANG definitions.


## Solution

* pyangbind
* ncclient



```asciiart 
| <pyangbind> rbindings.[rpc_command].input() ->> <ncclient> .rpc.call() ->> <network device>
| <pyangbind> rbindings.[rpc_command].output() <<- <ncclient> <<-      .xml() <network device>
|
|

```

