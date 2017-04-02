from flask import Flask, render_template, request, json, url_for, redirect
from flask_basicauth import BasicAuth
from werkzeug.utils import secure_filename
from PIL import Image

import data_import_functions as imp
import os


#image upload path
if os.environ.get("IS_HEROKU"):
	UPLOAD_FOLDER = '/tmp'
else:
	UPLOAD_FOLDER = 'tmp'


ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

#image upload checking

def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)


@app.route('/')
def hello_world():
	track_data = imp.get_single_track_data()

	return render_template('index.html', track_info = track_data)

@app.route('/verify', methods=['POST'])
def handle_data():
	filename = ''
	#get image file

	return render_template('verify.html')

@app.route('/embed_player')
def embed():
    uri = request.args.get('uri')
    print(request.args)
    contents = imp.get_embed_contents(uri)
    return render_template('embed_player.html', contents=contents)

@app.route('/confirm', methods=['GET', 'POST'])
def show_confirmation():
	return 'confirmedddd'