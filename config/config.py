class Config:
    DEBUG = True
    SECRET_KEY = ''
    
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'admin'
    MYSQL_DB = 'bnb_database'
    
    UPLOAD_FOLDER = 'static/img/rooms'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}