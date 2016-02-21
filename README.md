# Persuade Compucorp setup and documentation.

## Description:

This document is intented to be a documentation and setup guide for Compucorp devops position technical test.

## Prerequisites:
AWS work:
> create a user with generated keys and with a policy enabled to admin EC2/VPC

> create a s3 bucket where store the backups.

> create a user with generated keys and with a policy enabled to write in the s3 bucket

Developer machine: before you run any script, it's mandatory setting up the basic software for running them. This is:
> python (tested with version 2.7.10) and python-dev

> pip (tested with version 6.0.8)

## Structure

> conf: directory holding every configuration files, each in its own related folder.

> vendor: 3rd party software needed.

> src: automation process related source files.

> etl: pentaho kettle data integration files.

## Set up

> Install virtualenv: 

    sudo pip install virtualenv

> Create virtualenv: 

    virtualenv $HOME/.virtualenv/compu

> Activate it: 

    source $HOME/.virtualenv/compu/bin/activate

> Go to the project folder of your choice (ie $HOME/prj): 

    cd $HOME/prj

> Clone the repository

    git clone https://github.com/periket2000/prj.git

> Install dependencies: 

    pip install -r conf/python/requirements.txt

At this point we're ready to rock!

Edit the aws.conf config file for setting up the aws keys, backup bucket and s3 keys.

    vim conf/python/aws.conf

> (mandatory: **aws_access_key_id/aws_secret_access_key** for EC2/VPC setup)

> (mandatory: **s3id/s3key** for S3 bucket access, should have restricted access to s3)

> (mandatory: **bucket** existing bucket in s3 for storing the backups)
    
after the parameters setup, simply run the following command:

    cd src && python compu_main.py

After a while, you'll have got the desired environment up, configured and running.
Just connect to it with:

    ssh -i /tmp/compu_key.pem admin@ip_displayed_in_the_instalation_process

Check whatever you want.

## Backup strategy

Once deployed, we'll have a scheduled process to backup our site to s3 bucket. What we backup is drupal and civi databases as well as the whole site. This process could be refined by doing weekly full backups plus incremental daily backups.
