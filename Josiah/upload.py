import subprocess
import sys
import os
import pexpect
import hashlib

def hash_file(filepath): # GPT function, used to check that the file is the same
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):  # Read in chunks
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

# Example usage
# file_path = "PMBus.py"
# print(f"SHA-256: {hash_file(file_path)}")

def upload_to_board(lst):
    # All lists follow the form (repeat)
    # 1. Source location
    # 2. user (default = root)
    # 3. board_ip
    # 4. destination (default = "/home/root"
    fileLocationLocal = lst[0]
    usr = lst[1]
    ipAddress = lst[2]
    dest = lst [3]

    # check 1
    if not os.path.isfile(fileLocationLocal): # if it is not a file
        print(f"The file {fileLocationLocal} does not exist")
        return # reject

    # check 2
    # this one we skip
    if usr is None:
        usr = "root" # default
    # check 3
    #temp func, will rewrite
    if not ping_host(ipAddress):
        print(f"Ping failed at: {ipAddress}")
        # setup the connection
        return # reject
    # run the command "sudo ip route add 192.168.9.0/24 dev enp1s0" to add the route to the board
    print("Attempting to set up the connection")
    # try:
    #     subprocess.run("sudo ip route add 192.168.9.0/24 dev enp1s0", shell=True, check=True)
    #     print("Connection setup successful, proceeding with upload")
    # except subprocess.CalledProcessError as e:
    #     print(f"Failed to set up connection: {e}")

    # check 4
    # this one we skip
    print("All checks passed")

    # if all pass, then we can run the scp command
    cmd = f"scp {fileLocationLocal} {usr}@{ipAddress}:{dest}"
    print(cmd)

    try:
        print(f"Executing command: {cmd}")

        child = pexpect.spawn(cmd)
        # child.expect('password:')
        # child.sendline('root')
        for line in child: # progress bar
            print(f"Line: {line.decode('utf-8').strip()}")

        print("Copied successfully")

        print(f"Current Hash of {fileLocationLocal}:")
        print(hash_file(fileLocationLocal))
    except Exception as e:
        print(f"Error: {e}")


def ping_host(host, count=1, timeout=2):
    try:
        # Ping command depends on platform; this works on Linux/macOS
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0 # success
    except Exception:
        return False


# Example usage:
if __name__ == "__main__":

    board_ip = "192.168.9.2"
    base = "/run/media/mmcblk0p1/capsnet/bin"
    testingbase = "/run/media/mmcblk0p1/capsnet"
    xBase = "/run/media/mmcblk0p1/capsnet/model"
    user = "root"
    # ssh-keygen -f "/home/beta/.ssh/known_hosts" -R "192.168.9.2"

    startLocation = "../../P4P-CapsuleNetworkAccelerator/accel/app/CapsuleNetwork/bin/CapsuleNetwork.exe"
    testLocation = "../../P4P-CapsuleNetworkAccelerator/accel/app/CapsuleNetwork/linux/testing.sh"
    testLocation2 = "../../P4P-CapsuleNetworkAccelerator/accel/app/CapsuleNetwork/linux/testing2.sh"
    xmodelLocation = "../../P4P-CapsuleNetworkAccelerator/accel/app/CapsuleNetwork/linux/model/partial_caps.xmodel"
    setupLocation = "../../P4P-CapsuleNetworkAccelerator/accel/app/CapsuleNetwork/linux/setup.sh"
    validateLocation = "validate.py"
    pmnew = "PMNew.py"
    # All lists follow the form
    # 1. Source location
    # 2. user (default = root)
    # 3. board_ip (defined above, otherwise defaults 192.168.9.2)
    # 4. destination (default = "/home/root"
    if not ping_host(board_ip): # check if the board is alive before we do anything
        print("Board is not reachable")
        sys.exit(1)
    else:
        print("Board is reachable, proceeding with upload")

    # upload_to_board([testLocation, user, board_ip, testingbase]) # testing script
    # upload_to_board([testLocation2, user, board_ip, testingbase]) # testing script 2
    # upload_to_board([xmodelLocation, user, board_ip, xBase]) # xmodel
    # upload_to_board([setupLocation, user, board_ip, testingbase]) # setup
    # upload_to_board([validateLocation, user, board_ip, testingbase]) # validation script
    # upload_to_board([startLocation, user, board_ip, base]) # CapsuleNetwork.exe
    upload_to_board([pmnew, user, board_ip, testingbase]) # PMNew.py

    # bottom line is ~0.54
    # last known 100% acc is 0.56 but before also fails will need to run with more files to test properly