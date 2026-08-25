sudo umount /dev/mmcblk0p*
sudo dd if=sd_card.img of=/dev/mmcblk0 bs=4M status=progress conv=fsync
sync
sudo mkdir -p /mnt/sdroot1
sudo mkdir -p /mnt/sdroot2
sudo mount /dev/mmcblk0p1 /mnt/sdroot1
sudo mount /dev/mmcblk0p2 /mnt/sdroot2
sudo cp -R "./capsnet" "/mnt/sdroot1"
# sudo cp "/mnt/sdroot1/dpu.xclbin" "/mnt/sdroot1/four_kernels.xclbin"
sudo cp -R "/mnt/sdroot1/capsnet/smbus2" "/mnt/sdroot2/usr/lib/python3.9"

