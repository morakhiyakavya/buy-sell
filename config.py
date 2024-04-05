import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    """All application configurations"""

    # Web form security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-cannot-guess'

    # Database configurations
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    ADMINS = ['ADMINS']

    # Deployment
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
