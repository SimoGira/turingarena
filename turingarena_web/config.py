# configuration file for TuringArena Web

# debug mode
DEBUG = True

# secret key - set a random value in production
SECRET_KEY = "ciao"

# set log level
LOG_LEVEL = "DEBUG"

# allow users to create an account
ALLOW_REGISTRATION = True

# database credentials
DB_NAME = "turingarena"
DB_USER = "turingarena"
DB_PASS = "turingarena"
DB_HOST = "localhost"

# allowed languages
ALLOWED_LANGUAGES = ["python"]

# where to put problem files
PROBLEM_DIR_PATH = "/home/ale/tweb/problem/{name}"

# where to save submission for problems
SUBMITTED_FILE_PATH = "/home/ale/tweb/submission/{username}/{problem_name}/{timestamp}_{filename}"
