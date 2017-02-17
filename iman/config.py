#!/usr/bin/env python
import os

class Config(object):
    BIND = '0.0.0.0'
    PORT = 7003
    DEBUG = False
    CSRF_ENABLED = True
    SECRET_KEY = os.urandom(24)
    APPLICATION_ROOT = '/iman'
    CDN_BOOTSTRAP = "//maxcdn.bootstrapcdn.com/bootstrap/3.3.7"
    CDN_FONTAWESOME = "//maxcdn.bootstrapcdn.com/font-awesome/4.7.0"
#    CDN_COMMON = ''
#    CDN_DATATABLES = ''
#    CDN_MAVAPA = ''
    DB_DEBUG = False
    DB_TYPE = 'mysql'
    DB_PORT = 3306
    DB_NAME = 'iman'
    
class Production(Config):
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASS = 'root1234'
    SECRET_KEY = 'SWC3eezkau8khZ5LU1OH'
    MAVAPA_URL = 'https://accounts.example.com'
    CLIENT_ID = 'Qjh7ahdEsfdo8uDP0y48wB5w'
    CLIENT_SECRET = 'D3UwtbTBYYwnQVhx6A7B1jLg'
    REDIRECT_URI = 'https://manage.example.com/iman/oauth/code/'
    
class Staging(Config):
    DEBUG = True
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASS = 'root1234'
    SECRET_KEY = '4ZTW5sl8yJGcXqhsN3GA8gMo'
    MAVAPA_URL = 'https://accounts.stage.example.com'
    CLIENT_ID = 'h7rtOFG4YM4QpNAoti77e620'
    CLIENT_SECRET = 'COMH89RdFT733UVqH1GIQuI4'
    REDIRECT_URI = 'https://stage.example.com/iman/oauth/code/'
    
class Development(Config):
    DEBUG = True
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASS = '1234567890'
    MAVAPA_URL = 'http://accounts.dev.example.com'
    CLIENT_ID = 'M9V5FM3gadPRssNm4VPeEMOz'
    CLIENT_SECRET = 'mdlCloXKyG2yaduP9moSGztS'
    REDIRECT_URI = 'http://dev.example.com/iman/oauth/code/'
    
class Local(Config):
    DEBUG = True
    DB_DEBUG = True
    DB_HOST = 'localhost'
    DB_USER = 'app_iman'
    DB_PASS = '1234567890'
    MAVAPA_URL = 'http://localhost:7001/mavapa'
    CLIENT_ID = '6xXT7oYjcDlIFZQ9ELiVwoKE'
    CLIENT_SECRET = '5lCzRm2a68iDmEMSYFWKCDQs'
    REDIRECT_URI = 'http://localhost:7003/iman/oauth/code/'
