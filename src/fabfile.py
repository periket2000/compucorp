""" fab_test.py
 Fabric process
 No comments needed, self explanatory.
 Start in deploy() method to understand what's going on
"""
__author__ = 'Marco Albero'
from fabric.api import env, sudo, settings, hide, put, run
import ConfigParser
import os
from fabric.utils import warn
import urllib

# script dir
current_dir = os.path.dirname(os.path.abspath(__file__))

# environment
init = current_dir + '/../conf/python/aws.conf'
nginx_files = current_dir + '/../conf/deploy/nginx/'
drupal_files = current_dir + '/../conf/deploy/drupal/'
vendor_files = current_dir + '/../vendor/'
environment = 'environment'
default = 'default'
box = 'box'
general = 'general'
config = ConfigParser.ConfigParser()
config.read(init)

# fabric env conf
env.user = config.get(box, 'username')
env.key_filename = config.get(general, 'ssh_pubkey_path')


def test(host=None):
    if host:
        env.hosts = [host]
    set_up_backup(config.get(box, 'drupal_database'), 
                  'root', 
                  config.get(box, 'mysql_root_password'), 
                  'localhost',
                  config.get(box, 'civi_database_user'),
                  config.get(box, 'civi_database_password'),
                  config.get(box, 'civi_database'), 
                  config.get(box, 's3id'), 
                  config.get(box, 's3key'), 
                  config.get(box, 'bucket'))


def deploy(host=None):
    if host:
        env.hosts = [host]
    update()
    install_mysql()
    create_drupal_scheme(config.get(box, 'drupal_database'),
                         'root',
                         config.get(box, 'mysql_root_password'),
                         'localhost',
                         config.get(box, 'drupal_database_user'),
                         config.get(box, 'drupal_database_password'))
    generate_self_signed_certs()
    install_nginx()
    install_drush()
    install_git()
    install_drupal_site(config.get(box, 'drupal_project'))
    create_civi_scheme(config.get(box, 'civi_database'),
                         'root',
                         config.get(box, 'mysql_root_password'),
                         'localhost',
                         config.get(box, 'civi_database_user'),
                         config.get(box, 'civi_database_password'))
    install_civi()
    install_views()
    grant_on_scheme(config.get(box, 'civi_database')+'.*',
                    'root',
                    config.get(box, 'mysql_root_password'),
                    'localhost',
                    config.get(box, 'drupal_database_user'),
                    'select')
    install_backup()
    install_s3()
    set_up_backup(config.get(box, 'drupal_database'), 
                  'root', 
                  config.get(box, 'mysql_root_password'), 
                  'localhost',
                  config.get(box, 'civi_database_user'),
                  config.get(box, 'civi_database_password'),
                  config.get(box, 'civi_database'), 
                  config.get(box, 's3id'), 
                  config.get(box, 's3key'), 
                  config.get(box, 'bucket'))


def install_nginx():
    apt_get('php5-gd')
    apt_get('php5-fpm')
    apt_get('php5-curl')
    apt_get('nginx')
    file_send(nginx_files + 'default', '/etc/nginx/sites-available/default')
    sudo('sed -i "s|XXX_PROJECT_XXX|' + config.get(box, 'drupal_project') + '|g" /etc/nginx/sites-available/default')
    sudo('/etc/init.d/nginx restart')


def install_civi():
    file_send(vendor_files + 'civicrm-4.7.1-drupal.tar.gz', '/home/' + env.user, superuser=False)
    run('tar xvzf civicrm-4.7.1-drupal.tar.gz')
    run('mkdir -p /home/' + env.user + '/.drush')
    run('mv /home/' + env.user + '/civicrm/drupal/drush/civicrm.drush.inc /home/' + env.user + '/.drush')
    run('rm -fr /home/' + env.user + '/civicrm')
    sudo('cd /var/www/html/' + config.get(box, 'drupal_project') +' && drush --include=/home/' + env.user + '/.drush civicrm-install --dbuser=civicrm --dbpass=civicrm --dbhost=localhost --dbname=civicrm --tarfile=/home/' + env.user + '/civicrm-4.7.1-drupal.tar.gz --destination=sites/all/modules')
    sudo('chmod u+w /var/www/html/' + config.get(box, 'drupal_project') + '/sites/default')
    sudo('cd /var/www/html && chown -R www-data ' + config.get(box, 'drupal_project'))
    sudo('sed -i "s|http://default||g" /var/www/html/' + config.get(box, 'drupal_project') + '/sites/default/civicrm.settings.php')
    sudo('/etc/init.d/nginx restart')
    sudo('cd /var/www/html/' + config.get(box, 'drupal_project') +' && drush civicrm-api -u 1 job.execute')


def install_views():
    file_send(vendor_files + 'views-7.x-3.13.tar.gz', '/home/' + env.user, superuser=False)
    sudo('cd /var/www/html/' + config.get(box, 'drupal_project') + '/modules && tar xvzf /home/' + env.user + '/views-7.x-3.13.tar.gz')
    sudo('cd /var/www/html/' + config.get(box, 'drupal_project') + ' && drush -y en views')
    sudo('cd /var/www/html && chown -R www-data ' + config.get(box, 'drupal_project'))
    file_send(drupal_files + 'settings.php', '/home/' + env.user, superuser=False)
    run('sed -i "s|DRUPALDBXXX|' + config.get(box, 'drupal_database') + '|g" /home/' + env.user + '/settings.php')
    run('sed -i "s|DRUPALUSERXXX|' + config.get(box, 'drupal_database_user') + '|g" /home/' + env.user + '/settings.php')
    run('sed -i "s|DRUPALPWDXXX|' + config.get(box, 'drupal_database_password') + '|g" /home/' + env.user + '/settings.php')
    run('sed -i "s|CIVIDBXXX|' + config.get(box, 'civi_database') + '|g" /home/' + env.user + '/settings.php')
    sudo('mv /home/' + env.user + '/settings.php /var/www/html/' + config.get(box, 'drupal_project') + '/sites/default/.')
    sudo('chown www-data:root /var/www/html/' + config.get(box, 'drupal_project') + '/sites/default/settings.php')
    sudo('chmod 444 /var/www/html/' + config.get(box, 'drupal_project') + '/sites/default/settings.php')


def install_backup():
    file_send(vendor_files + 'backup_migrate-7.x-3.1.tar.gz', '/home/' + env.user, superuser=False)
    sudo('cd /var/www/html/' + config.get(box, 'drupal_project') + '/modules && tar xvzf /home/' + env.user + '/backup_migrate-7.x-3.1.tar.gz')
    sudo('cd /var/www/html/' + config.get(box, 'drupal_project') + ' && drush -y en backup_migrate')
    sudo('cd /var/www/html && chown -R www-data ' + config.get(box, 'drupal_project'))


def install_s3():
    file_send(vendor_files + 'tpyo-amazon-s3-php-class-v0.5.1-2-g928bb51.tar.gz', '/home/' + env.user, superuser=False)
    sudo('cd /var/www/html/' + config.get(box, 'drupal_project') + '/modules/backup_migrate/includes && tar xvzf /home/' + env.user + '/tpyo-amazon-s3-php-class-v0.5.1-2-g928bb51.tar.gz --strip-components=1')
    sudo('cd /var/www/html && chown -R www-data ' + config.get(box, 'drupal_project'))


def install_drush():
    apt_get('drush')


def install_git():
    apt_get('git')


def file_send(localpath, remotepath, superuser=True):
    put(localpath, remotepath, use_sudo=superuser)


def update():
    """
    Updates the package list
    """
    sudo("dpkg -l | grep linux-image | awk '{print $2 \" hold\"}' | sudo dpkg --set-selections")
    sudo("dpkg -l | grep grub | awk '{print $2 \" hold\"}' | sudo dpkg --set-selections")
    sudo('apt-get update -qq')
    sudo('apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" dist-upgrade')


def apt_get(*packages):
    sudo('apt-get -y --no-upgrade install %s' % ' '.join(packages), shell=False)


def generate_self_signed_certs():
    sudo('openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/ssl-cert-snakeoil.key -out /etc/ssl/certs/ssl-cert-snakeoil.pem')


def install_mysql():
    with settings(hide('warnings', 'stderr'), warn_only=True):
        result = sudo('dpkg-query --show mysql-server')
    if result.failed is False:
        warn('MySQL is already installed')
        return
    mysql_password = config.get(box, 'mysql_root_password')
    sudo('echo "mysql-server-5.0 mysql-server/root_password password %s" | debconf-set-selections' % mysql_password)
    sudo('echo "mysql-server-5.0 mysql-server/root_password_again password %s" | debconf-set-selections' % mysql_password)
    apt_get('mysql-server')


def grant_on_scheme(database_tables, user, password, host, granted, grant):
    run('echo "grant %s on %s to \'%s\'@\'localhost\';"|mysql --batch --user=%s --password=%s --host=%s' % (grant, database_tables, granted, user, password, host), pty=True)


def create_drupal_scheme(database, user, password, host, drupal_user, drupal_password):
    run('echo "CREATE USER \'' + drupal_user + '\'@\'localhost\' IDENTIFIED BY \'' + drupal_password + '\';"|mysql --batch --user=%s --password=%s --host=%s' % (user, password, host), pty=True)
    run('echo "CREATE DATABASE %s;"|mysql --batch --user=%s --password=%s --host=%s' % (database, user, password, host), pty=True)
    run('echo "GRANT ALL ON ' + database + '.* TO \'' + drupal_user + '\'@\'localhost\';"|mysql --batch --user=%s --password=%s --host=%s' % (user, password, host), pty=True)


def create_civi_scheme(database, user, password, host, civi_user, civi_password):
    run('echo "CREATE USER \'' + civi_user + '\'@\'localhost\' IDENTIFIED BY \'' + civi_password + '\';"|mysql --batch --user=%s --password=%s --host=%s' % (user, password, host), pty=True)
    run('echo "CREATE DATABASE %s;"|mysql --batch --user=%s --password=%s --host=%s' % (database, user, password, host), pty=True)
    run('echo "GRANT ALL ON ' + database + '.* TO \'' + civi_user + '\'@\'localhost\';"|mysql --batch --user=%s --password=%s --host=%s' % (user, password, host), pty=True)


def install_drupal_site(project):
    sudo('cd /var/www/html && drush -y dl drupal --drupal-project-rename='+project)
    sudo('cd /var/www/html/' + project + ' && drush -y site-install standard --db-url=\'mysql://drupal:drupal@localhost/drupal\' --site-name=' + project)
    sudo('mkdir -p /var/www/html/' + project + '/sites/default/files/public')
    sudo('mkdir -p /var/www/html/' + project + '/sites/default/files/private')
    sudo('echo "HI!" > /var/www/html/' + project + '/sites/default/files/public/hi.txt')
    sudo('echo "HI!" > /var/www/html/' + project + '/sites/default/files/private/hi.txt')
    sudo('chown -R www-data /var/www/html/' + project)
    sudo('cd /var/www/html/' + project + ' && drush upwd --password="' + config.get(box, 'drupal_admin_password') + '" "admin"')
    sudo('/etc/init.d/nginx restart')


def set_up_backup(database, user, password, host, civiuser, civipwd, cividb, s3id, s3key, bucket, destination_name="compucorps3", schedule_name="s3_backup", cron="0 4 * * *"):
    run('echo "INSERT INTO '+database+'.backup_migrate_destinations VALUES (\'1\',\''+destination_name+'\',\''+destination_name+'\',\'s3\',\'https://'+s3id+':'+urllib.quote_plus(s3key)+'@s3.amazonaws.com/'+bucket+'\',\'a:0:{}\');"|mysql --batch --user=%s --password=%s --host=%s' % (user, password, host), pty=True)
    run('echo "INSERT INTO '+database+'.backup_migrate_schedules VALUES (\'1\',\''+schedule_name+'\',\''+schedule_name+'\',\'archive\',\''+destination_name+'\',\'\',\'default\',\'0\',\'86400\',\'1\',\'builtin\',\''+cron+'\');"|mysql --batch --user=%s --password=%s --host=%s' % (user, password, host), pty=True)
    run('echo "INSERT INTO '+database+'.backup_migrate_sources VALUES (\'1\',\'mysql_civi\',\'Mysql civi\',\'mysql\',\'mysql://'+civiuser+':'+civipwd+'@localhost/'+cividb+'\',\'a:0:{}\');"|mysql --batch --user=%s --password=%s --host=%s' % (user, password, host), pty=True)
