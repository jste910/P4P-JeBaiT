me=open("recovered/raw.csv","r")
g=open("recovered/processed.csv","w")

help = open("recovered/help.txt","w")
# open all the logs in /recovered/v1_100MHz/ and process them into a single file
for i in range(85,80,-1):
    with open(f"recovered/0.{i}V/log.txt","r") as f:
        for line in f:
            help.write(line)
help.close()

h = open("recovered/help.txt", "r")
outputfile = open("merge.txt", "w")
# while both h and me have not run out of lines, read a line from each and compare the timestamps
l1 = h.readline()
l2 = me.readline() # ignore
l2 = me.readline()
save1 = str(0)
save2 = str(0)

while True:

    # print(l1.split(",")[0].strip().split(" ")[0], l2.split(",")[0].strip())

    if not l1 and not l2:
        break # both files are done

    time1 = (l1.split(",")[0].strip().split(" ")[0])
    time2 = (l2.split(",")[0].strip())

    print(f"l1: {time1} l2: {time2} save1: {save1} save2: {save2}")

    if time1 == "":
        # write the rest of me
        while l2:
            outputfile.write(l2)
            l2 = me.readline()
        break
    if time2 == "":
        while l1:
            outputfile.write(l1)
            l1 = h.readline()

    if time1 < time2:
        outputfile.write(l1)
        l1 = h.readline()
    elif time1 > time2:
        outputfile.write(l2)
        l2 = me.readline()
    else: # equal
        print("MATCHING TIME SIGNATURE")
        outputfile.write(l1)
        outputfile.write(l2)
        l1 = h.readline()
        l2 = me.readline()

me.close()
outputfile.close()
h.close()

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
# l = me.readline()
# g.write(l)
# l=l.split(',')
k = "timestamp_monotonic_ns,record_type,phase,event,detail,measurement_index,image_index,requested_vccint_v, sample_start_ns, sample_end_ns,"

rails = {"VCCINT" : "PMBUS",
        "VCCBRAM" : "PMBUS",
        "VCCPSINTFP" : "PMBUS",
        "DDR4_DIMM_VDDQ" : "PMBUS",
        "VCCPSINTLP" : "PMBUS",
        "VCCO_PSDDR_504" : "HWMON",
        "VCCAUX" : "PMBUS",
        }

railspt2 = ["PMBUS", "PMBUS", "PMBUS", "PMBUS", "PMBUS", "HWMON", "PMBUS"]

# rails = {"VCCINT" : "PMBUS",
#         }
for r in rails:
    k += f"{r}_path,{r}_voltage_v,{r}_current_a,{r}_power_w,{r}_vi_power_w,{r}_power_difference_w,{r}_valid,{r}_error,"

for r in rails:
    k += f"{r}_temperature,"

print(k)
g.write(k + "\n")
# safeexit()


measurementstart = False
current_voltage = 0.85
# time, event|sample, phase(nothing), event, MEASUREMENTSTART, detail?, measurement?, index?
me=open("merge.txt","r")


for line in me:
    writeme = ""
    a = line.strip().split(",")
    if len(a) == 31: # this is a measurement line
        if measurementstart:
            # write this
            a=a[:-1] # remove the last empty element
            w = a[0] + "," + "SAMPLE" + f",,,,,,,{a[0]},{a[-1]}," 
            a=a[1:-1] # remove the first and last element

            for i in range(0, len(a), 4):
                w += f"{railspt2[i//4]},{decode_vout(int(a[i]))},{decode_linear11(int(a[i+1]))},,{decode_vout(int(a[i]))*decode_linear11(int(a[i+1]))},,1,,"
                print(a[i], a[i+1], a[i+2], a[i+3])

            for i in range(0, len(a), 4):
                print(a[i+2])
                w += f"{decode_linear11(int(a[i+2]))},"

            g.write(w + "\n")
    if len(a) == 2: # this is a default line
        writeme = a[0] + "," + "EVENT," + "," + a[1] + ","*25
        if a[1].strip() == "MEASUREMENT_START":
            measurementstart = True
        if a[1].strip() == "MEASUREMENT_END":
            measurementstart = False
        g.write(writeme + "\n")

me.close()
g.close()