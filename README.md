# nextcloud-mail-collector
A small script to be run on NextCloud host or on any other instance.
It aimed to collect attachments from certain email box and then upload them to NextCloud over WebDAV.

### Description ###

Written in python3, based on mail-attachment-archiver by [auino](https://github.com/auino/mail-attachments-archiver)

### Configuration ###

 - Place script somewhere in filesystem. Ie `/opt/nextcloud_scripts`
 - Add permissions to user, from which you plan to run this script, ie `chown www-data:www-data /opt/nextcloud_scripts -R`
 - Edit the `nextcloud-mail-collector.py` file content by configuring the program and customizing its behavior.
 - Add your script to cron, ie
   - `sudo -u www-data crontab -e`
   - `*/2  *  *  *  * /opt/nextcloud_scripts/mail-attachments-archiver.py > /dev/null 2>&1` to run it every 2 min
