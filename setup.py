# -*- coding: utf-8 -*-
from distutils.core import setup

setup(name='s3mysqlbkp',
    version='1.2',
    description='MySQL backups to Amazon S3',
    author='Daniel Yavorovich',
    author_email='yavorovich@denni.org',
    url='https://github.com/daniel-yavorovich/s3mysqlbkp',
    license='GPL',
    platforms = ('Linux',),
    keywords = ('amazon', 'mysql', 's3', 'backup'),
    packages=['s3mysqlbkp'],
    package_dir={'s3mysqlbkp': 'src/s3mysqlbkp'},
    scripts = ['bin/s3mysqlbkp_run.py'],
    download_url = 'http://pip.hosting4django.net/s3mysqlbkp-1.2.tar.gz',
    data_files=[
        ('../etc', ['cfg/s3mysqlbkp.conf']),
    ],
    requires=['boto (>=2.7.0)'],
)

