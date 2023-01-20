"""Binary helper for tplink_ess_lib."""


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
