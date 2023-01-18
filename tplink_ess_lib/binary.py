"""Binary helper for tplink_ess_lib."""

SEP = ","


def ports2list(ports):
    """Convert ports to a list."""
    if ports is None:
        port_list = []
    else:
        try:
            port_list = [int(x) for x in ports.split(SEP)]
        except ValueError:
            port_list = []
    return port_list


def ports2byte(ports):
    """Convert ports to bytes."""
    out = 0
    port_list = ports2list(ports)
    if port_list == []:
        out = 0
    else:
        for i in port_list:
            out |= 1 << (int(i) - 1)
    return out


def byte2ports(byte):
    """Convert bytes to ports."""
    out = []
    for i in range(32):
        if byte % 2:
            out.append(str(i + 1))
        byte >>= 1
    return SEP.join(out)


def mac_to_bytes(mac):
    """Convert mac address to bytes."""
    return bytes(int(byte, 16) for byte in mac.split(":"))


def mac_to_str(mac):
    """Convert mac bytes to a string."""
    return ":".join(format(s, "02x") for s in mac)
