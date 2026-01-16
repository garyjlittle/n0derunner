# LVM Performance
My vm is called `lvmtest`
## Create disks in acli
```
<acropolis> vm.disk_create lvmtest container=default-container-76528194032531 create_size=25G
DiskCreate: complete
<acropolis> vm.disk_create lvmtest container=default-container-76528194032531 create_size=25G
DiskCreate: complete
<acropolis> vm.disk_create lvmtest container=default-container-76528194032531 create_size=25G
DiskCreate: complete
<acropolis> vm.disk_create lvmtest container=default-container-76528194032531 create_size=25G
DiskCreate: complete
```
## Create the volume group in Linux
Use the shorthand
```
nutanix@ubuntu-server:~$ sudo vgcreate 4DISKVG /dev/sd[cdef]

  Physical volume "/dev/sdc" successfully created.
  Physical volume "/dev/sdd" successfully created.
  Physical volume "/dev/sde" successfully created.
  Physical volume "/dev/sdf" successfully created.
  Volume group "4DISKVG" successfully created

```
## Create the logical volume in Linux
```
nutanix@ubuntu-server:~$ sudo lvcreate --type raid0 --stripes 4 --stripesize 1M -l +100%FREE -n 4DISKLV 4DISKVG
  Logical volume "4DISKLV" created.
```
## Check the stripe size
```
nutanix@ubuntu-server:~$ sudo lvs -o +stripe_size
  LV        VG        Attr       LSize   Pool Origin Data%  Meta%  Move Log Cpy%Sync Convert Stripe
  4DISKLV   4DISKVG   rwi-a-r---  99.98g                                                      1.00m
  ubuntu-lv ubuntu-vg -wi-ao---- <30.00g                                                         0
```

### Idenfity the dm device
```
root@ubuntu-server:/home/nutanix# ls -l /dev/mapper
total 0
lrwxrwxrwx 1 root root       7 Jan 16 02:14 4DISKVG-4DISKLV -> ../dm-5
```
### Test
### Write our fio for sequential workload
```
[global]
ioengine=libaio
direct=1
iodepth=32
rw=write
bs=1m
[writer]
filename=/dev/mapper/4DISKVG-4DISKLV
```

### Run the fio and observe the IO stream (sequential, 1MB io sizes)
```
root@ubuntu-server:/home/nutanix# iostat -xzm -p dm-5 1
```
Output: 5GBytes/s - IO size 1MB as requested in the stripe
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           2.27    0.00    1.26    0.00    0.00   96.47

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-5             0.00      0.00     0.00   0.00    0.00     0.00 5218.00   5218.00     0.00   0.00    5.84  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   30.49 100.00
```

### Write fio for small random workload
write size is 8K
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           3.06    0.00    7.65   12.76    0.00   76.53

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-5             0.00      0.00     0.00   0.00    0.00     0.00 113491.00    886.65     0.00   0.00    0.80     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   90.96 100.00
```

## Change stripe size to 8K
### Remove the old LV
```
nutanix@ubuntu-server:~$ sudo lvremove 4DISKVG 4DISKLV
Do you really want to remove and DISCARD active logical volume 4DISKVG/4DISKLV? [y/n]: y
```
### Create new LV
This time with 8K stripe
```
nutanix@ubuntu-server:~$ sudo lvcreate --type raid0 --stripes 4 --stripesize 8K -l +100%FREE -n 4DISKLV 4DISKVG
  Logical volume "4DISKLV" created.
```
## Re run fio
### Sequential 1M
Notice that the IO size is 8K since that's what we made the stripe size be.  Also not the huge queue length since each 1M IO is now split into 8K.  Performance is almost 1/2 what we achived from a 1M stripe size
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           1.29    0.00   10.34    0.00    0.00   88.37

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-5             0.00      0.00     0.00   0.00    0.00     0.00 356487.00   2785.05     0.00   0.00    9.55     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00 3404.82 100.00
```
### Random 8K
A bit better but not by much - so for these disks probably I would recommend 1MB stripe width/size
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           3.08    0.00    8.74   11.31    0.00   76.86

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-5             0.00      0.00     0.00   0.00    0.00     0.00 117155.00    915.27     0.00   0.00    0.79     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   92.49 100.00
```

## Reads
### Random read 8K on 8K stripe
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           2.60    0.00   10.91    8.83    0.00   77.66

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-5          156078.00   1219.36     0.00   0.00    0.53     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   83.42 100.00

```
### Random read 8K on 1M stripe
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           3.36    0.00   10.59    8.79    0.00   77.26

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-5          155585.00   1215.51     0.00   0.00    0.52     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   80.74 100.00
```
