me=open("recovered/me.csv","r")
g=open("new.csv","w")

def sign_extend(value, bits):
    """Sign-extend an integer encoded using the specified number of bits."""
    sign_bit = 1 << (bits - 1)
    return (value ^ sign_bit) - sign_bit

def decode_linear11(raw_word):
    """
    Decode a PMBus LINEAR11 value.

    Bits 15:11 contain a signed 5-bit exponent.
    Bits 10:0 contain a signed 11-bit mantissa.

    value = mantissa * 2**exponent
    """
    exponent = sign_extend((raw_word >> 11) & 0x1F, 5)
    mantissa = sign_extend(raw_word & 0x07FF, 11)
    return mantissa * (2.0 ** exponent)


def decode_vout(raw_word, exponent=-12):
    """
    Decode READ_VOUT for the ZCU102 MAX15301 VCCINT regulator.

    The device uses a fixed VOUT exponent of -12, so:
        voltage = raw_word / 4096
    """
    return raw_word * (2.0 ** exponent)

def safeexit():
    me.close()
    g.close()
    exit()
counter = 0


# auto write the first line
g.write(me.readline())

for line in me:
    counter+=1
    l=line.split(",")
    k = [l[0]]
    for i in range(4, (len(l)-1), 3):
        print(l[i-3], l[i-2], l[i-1], l[i])
        if l[i] == "65535": # we need to fix it
            # l[i-2] = str((decode_vout(int(l[i-2]), exponent=-12)))
            k.append(str((decode_vout(int(l[i-2]), exponent=-12))))
            # l[i-1] = str((decode_linear11(int(l[i-1]))))
            k.append(str((decode_linear11(int(l[i-1])))))
            k.append(str((decode_linear11(int(l[i])))))
            # l[i] = str(float(l[i-1]) * float(l[i-2]))
            k.append(str(decode_linear11(int(l[i-1])) * decode_vout(int(l[i-2]), exponent=-12)))
        # safeexit()
    li = ""
    for e in k:
        li += e + ","
    li = li[:-1]
    g.write(li[:-2]+'\n')




me.close()
g.close()