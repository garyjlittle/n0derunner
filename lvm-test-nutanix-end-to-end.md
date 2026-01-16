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
Full stripe - shows 1M all the way to the devices
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           2.53    0.00    1.26    0.00    0.00   96.21

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-1             0.00      0.00     0.00   0.00    0.00     0.00 1232.00   1232.00     0.00   0.00    6.03  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    7.43 100.00
dm-2             0.00      0.00     0.00   0.00    0.00     0.00 1231.00   1231.00     0.00   0.00    6.06  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    7.46  99.60
dm-3             0.00      0.00     0.00   0.00    0.00     0.00 1231.00   1231.00     0.00   0.00    6.44  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    7.93 100.00
dm-4             0.00      0.00     0.00   0.00    0.00     0.00 1232.00   1232.00     0.00   0.00    6.12  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    7.54  99.60
dm-5             0.00      0.00     0.00   0.00    0.00     0.00 4926.00   4926.00     0.00   0.00    6.18  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   30.42 100.00
sdc              0.00      0.00     0.00   0.00    0.00     0.00 1231.00   1231.00     0.00   0.00    6.03  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    7.42 100.00
sdd              0.00      0.00     0.00   0.00    0.00     0.00 1232.00   1232.00     0.00   0.00    6.10  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    7.52 100.00
sde              0.00      0.00     0.00   0.00    0.00     0.00 1232.00   1232.00     0.00   0.00    6.44  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    7.94 100.00
sdf              0.00      0.00     0.00   0.00    0.00     0.00 1232.00   1232.00     0.00   0.00    6.11  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    7.53 100.00
```
### Write fio for small random workload
```
[global]
ioengine=libaio
direct=1
iodepth=128
rw=randwrite
bs=8k
[writer]
filename=/dev/mapper/4DISKVG-4DISKLV
```
Output
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
Notice that the IO size is 8K since that's what we made the stripe size be.  Also not the huge queue length since each 1M IO is now split into 8K.  Performance is much lower than we achived from a 1M stripe size
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           3.34    0.00   13.37    0.00    0.00   83.29

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-5             0.00      0.00     0.00   0.00    0.00     0.00 476032.00   3719.00     0.00   0.00    4.57     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00 2175.03 100.00
```
Full stripe - the kernel is doing some merging for us
```
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-1             0.00      0.00     0.00   0.00    0.00     0.00 120086.00    938.17     0.00   0.00    5.33     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00  640.00 100.00
dm-2             0.00      0.00     0.00   0.00    0.00     0.00 120096.00    938.25     0.00   0.00    4.54     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00  545.13 100.00
dm-3             0.00      0.00     0.00   0.00    0.00     0.00 120041.00    937.82     0.00   0.00    4.60     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00  552.59 100.00
dm-4             0.00      0.00     0.00   0.00    0.00     0.00 120101.00    938.29     0.00   0.00    5.02     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00  603.24 100.00
dm-5             0.00      0.00     0.00   0.00    0.00     0.00 480209.00   3751.63     0.00   0.00    4.88     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00 2341.22 100.00
sdc              0.00      0.00     0.00   0.00    0.00     0.00 3738.00    934.50 116315.00  96.89    5.70   256.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   21.32 100.00
sdd              0.00      0.00     0.00   0.00    0.00     0.00 3738.00    934.50 116348.00  96.89    4.99   256.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   18.65 100.00
sde              0.00      0.00     0.00   0.00    0.00     0.00 3731.00    932.75 116321.00  96.89    5.03   256.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   18.77 100.00
sdf              0.00      0.00     0.00   0.00    0.00     0.00 3742.00    935.50 116343.00  96.88    5.40   256.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   20.21 100.00

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
### Write fio random read
```
[global]
ioengine=libaio
direct=1
iodepth=128
rw=randread
bs=8k
[reader]
filename=/dev/mapper/4DISKVG-4DISKLV
```
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
## Sequential read
### Seq read on 1M stripe
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           0.50    0.00    2.27    0.25    0.00   96.98

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-5          5801.00   5801.00     0.00   0.00    5.45  1024.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   31.59 100.00
```

### Seq read on 8k stripe
Even though the request size is 8K and the queueu is huge we still get decent performance probably read-ahead is helping here
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           0.00    0.00   22.53    0.00    0.00   77.47

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-5          652390.00   5096.80     0.00   0.00    3.33     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00 2170.66 100.00
```
Full stripe - we see that the kernel is merging the IO's and sending 256K requests to the storage device (in this case Nutanix HCI storage)
```
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           0.25    0.00   21.50    0.00    0.00   78.25

Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
dm-1          150713.00   1177.45     0.00   0.00    3.37     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00  508.03  94.40
dm-2          150702.00   1177.36     0.00   0.00    3.90     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00  588.38 100.00
dm-3          150688.00   1177.25     0.00   0.00    3.16     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00  476.82  94.80
dm-4          150713.00   1177.45     0.00   0.00    3.46     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00  521.28  94.80
dm-5          602741.00   4708.91     0.00   0.00    3.48     8.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00 2095.42 100.00
sdc           4717.00   1179.25 145976.00  96.87    3.51   256.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   16.54  94.40
sdd           4702.00   1175.50 146004.00  96.88    4.07   256.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   19.12 100.00
sde           4723.00   1181.00 145979.00  96.87    3.35   256.05    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   15.82  94.80
sdf           4716.00   1179.00 146004.00  96.87    3.56   256.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00   16.81  94.80
```
