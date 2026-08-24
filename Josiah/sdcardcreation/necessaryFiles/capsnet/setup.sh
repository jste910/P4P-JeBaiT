set -e

export XLNX_VART_FIRMWARE="/run/media/mmcblk0p1/capsnet/xclbin/four_kernels.xclbin"
echo $XLNX_VART_FIRMWARE

ip="192.168.9.2"

echo "Configuring IP to $ip"

ifconfig eth0 "$ip"

echo "Configured IP"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "File hashes:"

sha256sum "$SCRIPT_DIR/bin/CapsuleNetwork.exe"
sha256sum "$SCRIPT_DIR/testing.sh"
sha256sum "$SCRIPT_DIR/testing2.sh"
sha256sum "$SCRIPT_DIR/xclbin/four_kernels.xclbin"
sha256sum "$SCRIPT_DIR/model/partial_caps.xmodel"
