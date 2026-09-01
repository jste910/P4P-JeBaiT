set -e
export XLNX_VART_FIRMWARE="/run/media/mmcblk0p1/dpu.xclbin"
echo $XLNX_VART_FIRMWARE
ip="192.168.9.2"
echo "Configuring IP to $ip"
ifconfig eth0 "$ip"
echo "Configured IP"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd centos
./setup.sh
cd ..
echo "File hashes:"
sha256sum "/run/media/mmcblk0p1/dpu.xclbin"
sha256sum "$SCRIPT_DIR/PMNew.py"
export XLNX_VART_FIRMWARE="/run/media/mmcblk0p1/dpu.xclbin"
echo $XLNX_VART_FIRMWARE
scp -r ./me.csv beta@192.168.9.1:/home/beta/Desktop/P4P-JeBaiT/Josiah/recovered/"
