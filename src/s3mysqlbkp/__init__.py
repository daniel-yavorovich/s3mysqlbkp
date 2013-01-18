# -*- coding: utf-8 -*-

# Module backup MySQL dump and send to the server Amazon S3.

import os
import tarfile
import subprocess
import boto
import tempfile
import mimetypes
import logging
import ConfigParser
from datetime import datetime
from datetime import timedelta
from exceptions import Exception
from boto.s3.connection import Location
from boto.exception import S3CreateError
from boto.s3.connection import S3Connection

class S3MySQLBkp():

    def __init__(self, config_path):
        self.config_path = config_path

    def run_backup(self):
        self.backup_datetime = datetime.now().strftime('%F.%T')

        self.config = self._read_config(self.config_path)
        self.s3_conn = self._s3_connect_init()
        self._create_bucket()
        self._create_backups()
        self._upload_backups_to_s3()
        self._remove_tmp_file()
        self._remove_old_backups_from_s3()

    def _read_config(self, config_path):
        """
        Check s3mysqlbkp
        configuration file
        """

        if not os.path.isfile(config_path):
            raise IOError("Config file %s does not exist" % config_path)

        config = ConfigParser.RawConfigParser()
        config.read(config_path)
        return config

    def _s3_connect_init(self):
        return S3Connection(
            self.config.get('amazon', 'access_key'),
            self.config.get('amazon', 'secret_key')
        )

    def _create_bucket(self):
        try:
            self.s3_conn.create_bucket(self.config.get('amazon', 'bucket_name'), location=Location.USWest)
            logging.info("Bucket %s created" % self.config.get('amazon', 'bucket_name'))
        except Exception, error_description:
            if error_description.status != 409:
                raise error_description

    def _create_backups(self):
        # Create command processes
        mysqldump_schema_proc = subprocess.Popen(
            "mysqldump -h %s -u %s -p%s --verbose --quick --extended-insert --add-drop-database --add-drop-table --triggers --routines --no-data --databases %s" % (
                self.config.get('mysql', 'hostname'),
                self.config.get('mysql', 'username'),
                self.config.get('mysql', 'password'),
                self.config.get('mysql', 'databases'),
                ),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        mysqldump_data_proc = subprocess.Popen(
            "mysqldump -h %s -u %s -p%s --quick --complete-insert --extended-insert --insert-ignore --hex-blob --no-create-info --single-transaction --databases %s" % (
                self.config.get('mysql', 'hostname'),
                self.config.get('mysql', 'username'),
                self.config.get('mysql', 'password'),
                self.config.get('mysql', 'databases'),
                ),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        # Create temporary files
        mysqldump_schema_tmpfile = tempfile.NamedTemporaryFile()
        mysqldump_data_tmpfile   = tempfile.NamedTemporaryFile()

        # Run mysqldump command and write output to the temporary files
        mysqldump_schema_tmpfile.write(mysqldump_schema_proc.communicate()[0])
        mysqldump_data_tmpfile.write(mysqldump_data_proc.communicate()[0])

        # Flush temporary files
        mysqldump_schema_tmpfile.flush()
        mysqldump_data_tmpfile.flush()

        # Compress mysql dumps
        tar = tarfile.open(os.path.join(self.config.get('backup', 'tmp_dir'), "%s.tar.gz" % self.backup_datetime), "w|gz")
        tar.add(mysqldump_schema_tmpfile.name, "schema.sql")
        tar.add(mysqldump_data_tmpfile.name, "data.sql")

        # Add files to archive
        try:
            backup_files_list = self.config.get('files', 'paths').split(' ')
        except ConfigParser.NoSectionError:
            backup_files_list = []

        for file_path in backup_files_list:
            if not os.path.isfile(file_path):
                continue
            tar.add(file_path)

        # Remove temporary files
        mysqldump_schema_tmpfile.close()
        mysqldump_data_tmpfile.close()

        # Close tar archive
        tar.close()

    def _upload_backups_to_s3(self):
        bucket = self.s3_conn.get_bucket(self.config.get('amazon', 'bucket_name'))
        key = bucket.new_key("%s.tar.gz" % self.backup_datetime)
        key.set_contents_from_filename(os.path.join(self.config.get('backup', 'tmp_dir'), "%s.tar.gz" % self.backup_datetime))
        key.set_acl('private')

    def _remove_tmp_file(self):
        os.unlink(os.path.join(self.config.get('backup', 'tmp_dir'), "%s.tar.gz" % self.backup_datetime))

    def _remove_old_backups_from_s3(self):
        bucket = self.s3_conn.lookup(self.config.get('amazon', 'bucket_name'))
        for key in bucket:
            last_modified = datetime.strptime(key.last_modified, '%Y-%m-%dT%H:%M:%S.000Z')
            difference_time = datetime.now() - last_modified
            if difference_time.days > self.config.getint("backup", "max_lifetime_backup"):
                bucket.delete_key(key.name)