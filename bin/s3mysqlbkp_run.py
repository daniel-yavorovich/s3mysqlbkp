#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This script starts the process of creating a backup copy of the database
# and load it to the server Amazon S3, according to the settings in /etc/s3mysqlbkp.conf

from s3mysqlbkp import S3MySQLBkp

CONFIG_FILE = "/etc/s3mysqlbkp.conf"

# Init S3MySQLBkp class
s3bkp = S3MySQLBkp(CONFIG_FILE)

# Run backup
s3bkp.run_backup()