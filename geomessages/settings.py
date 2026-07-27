import dj_database_url

INSTALLED_APPS = [
    'django.contrib.gis',  
    'rest_framework',
    'rest_framework.authtoken', 
    'geo_app',
]

DATABASES = {
    'default': dj_database_url.config(default='postgis://geouser:geopassword@localhost:5432/geodb')
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated', 
    ]
}
