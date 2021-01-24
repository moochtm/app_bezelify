from app import app
from app.utils import bezelify

from flask import render_template, request, redirect, session, jsonify, send_from_directory, send_file
from werkzeug.utils import secure_filename
import uuid
from io import StringIO
import os
import shutil
import mimetypes
from datetime import timedelta, datetime
import zipfile
import json

app.config['UPLOAD_FOLDER'] = os.path.dirname(os.path.abspath(__file__)) + '/temp/'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.mkdir(app.config['UPLOAD_FOLDER'])

ALLOWED_IMAGE_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS
session_timeout_mins = 60

bezelify.get_bezels_metadata(force_refresh=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def set_folder(root_folder, rel_folder):
    root_folder['relative_path'] = rel_folder
    root_folder['absolute_path'] = os.path.join(app.config['UPLOAD_FOLDER'], rel_folder)
    if not os.path.exists(root_folder['absolute_path']):
        os.mkdir(root_folder['absolute_path'])


def refresh_bezels():
    # receives session images dict (or image dict)
    # go through temp folder
    # move new files into src folder
    # passes session images dict to bezelify
    # returns images json to populate table

    session['images'] = {}

    # move image files to src folder
    for i in os.listdir(session['temp_folder']['absolute_path']):
        if allowed_image_file(i):
            i_path = os.path.join(session['temp_folder']['absolute_path'], i)
            shutil.move(i_path, os.path.join(session['src_folder']['absolute_path'], i))

    # create list of images
    for f in os.listdir(session['src_folder']['absolute_path']):
        id = str(uuid.uuid4())
        session['images'][id] = {}
        session['images'][id]['src_file'] = os.path.join(session['src_folder']['relative_path'], f)

    print(session['images'])
    return session['images']


@app.before_request
def make_session_permanent():
    # SESSION STUFF
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=session_timeout_mins)

    if 'id' not in session.keys():
        session['id'] = str(uuid.uuid4())
    print("user session: " + session['id'])

    session['temp_folder'] = {}
    set_folder(root_folder=session['temp_folder'], rel_folder=session['id'])

    session['src_folder'] = {}
    set_folder(root_folder=session['src_folder'], \
               rel_folder=os.path.join(session['temp_folder']['relative_path'], 'src_folder'))

    session['dst_folder'] = {}
    set_folder(root_folder=session['dst_folder'], \
               rel_folder=os.path.join(session['temp_folder']['absolute_path'], 'dst_folder'))

    if 'images' not in session.keys():
        session['images'] = {}

    # CLEAN UP WIP STORAGE FOLDER
    print("cleaning up temp folder")
    for d in os.listdir(app.config['UPLOAD_FOLDER']):
        print("checking folder: " + str(d))
        path = os.path.join(app.config['UPLOAD_FOLDER'], d)
        mod_timestamp = datetime.fromtimestamp(os.path.getmtime(path))
        # IF NOW IS > 1 HR FROM DIR LAST MOD TIME, THEN DELETE
        if (datetime.now() - mod_timestamp).total_seconds() > session_timeout_mins * 60:
            print("deleting folder: " + str(d))
            shutil.rmtree(path)
            print("deleting: " + d)


@app.route("/", methods=['GET'])
def index():

    return render_template("public/index.html")


@app.route("/image/<image_id>", methods=['GET'])
def image(image_id):
    print(session['images'])

    if image_id in session['images'].keys():
        filename = session['images'][image_id]['src_file']
        folder = os.path.join(session['src_folder']['absolute_path'])
        print(folder, filename)

        if "bezel" in request.args:
            print(request.args["bezel"])

            stretch = False
            if "stretch" in request.args:
                if request.args["stretch"] == 'true':
                    stretch = True

            crop = False
            if "crop" in request.args:
                if request.args["crop"] == 'true':
                    crop = True

            preview = False
            if "preview" in request.args:
                if request.args["preview"] == 'true':
                    preview = True

            # GET BEZEL HERE
            src_path = os.path.join(session['src_folder']['absolute_path'], filename)
            dst_path = os.path.join(session['dst_folder']['absolute_path'], filename)
            shutil.copyfile(src_path, dst_path)
            file_to_send = bezelify.add_bezel(fp=dst_path, bezel_id=request.args["bezel"], stretch=stretch, crop=crop, preview=preview)

            if file_to_send is None:
                print("bezel could not be added, returning source image")
                return send_from_directory(folder, filename)

            folder, filename = os.path.split(file_to_send)
            # Get mimetype for file to send
            mt = mimetypes.types_map[os.path.splitext(filename)[1]]

            def generate():
                with open(file_to_send, 'rb') as f:
                    yield from f
                os.remove(file_to_send)

            response = app.response_class(generate(), mimetype=mt)
            response.headers.set('Content-Disposition', 'attachment', filename=filename)
            return response

        else:
            return send_from_directory(folder, filename)


@app.route('/upload_file', methods=['POST'])
def upload_file():

    # check if the post request has the file part
    if 'files[]' not in request.files:
        resp = jsonify({'message': 'No file part in the request'})
        resp.status_code = 400
        return resp

    files = request.files.getlist('files[]')

    errors = {}
    success = False

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            folder = session['src_folder']['absolute_path']
            file.save(os.path.join(folder, filename))
            success = True
        else:
            errors[file.filename] = 'File type is not allowed'

    bob = refresh_bezels()

    if success and errors:
        errors['message'] = 'File(s) successfully uploaded'
        resp = jsonify(errors)
        resp.status_code = 206
        return resp
    if success:
        resp = jsonify({'message': 'Files successfully uploaded'})
        resp.status_code = 201
    else:
        resp = jsonify(errors)
        resp.status_code = 400
    return resp


@app.route("/image_list", methods=['GET'])
def get_image_list():
    # receives session images dict (or image dict)
    # go through temp folder
    # move new files into src folder
    # passes session images dict to bezelify
    # returns images json to populate table

    session['images'] = {}

    # move image files to src folder
    for i in os.listdir(session['temp_folder']['absolute_path']):
        if allowed_image_file(i):
            i_path = os.path.join(session['temp_folder']['absolute_path'], i)
            shutil.move(i_path, os.path.join(session['src_folder']['absolute_path'], i))

    # create list of images
    for f in os.listdir(session['src_folder']['absolute_path']):
        id = str(uuid.uuid4())
        session['images'][id] = {'src_file': f}
    print(session['images'])
    return session['images']


@app.route("/bezel_list", methods=['GET'])
def get_bezel_list():

    bezels = bezelify.get_bezels_metadata()

    print(bezels)
    return bezels


@app.route("/delete_images", methods=['POST'])
def delete_images():

    print("delete")
    files = request.get_json(force=True)['files']
    print(files)

    folder = session['src_folder']['absolute_path']
    fails = []
    for file in files:
        path = os.path.join(folder, file)
        print("deleting: " + path)
        try:
            os.remove(os.path.join(folder, file))
        except:
            fails.append(file)

    if len(fails) > 0:
        resp = jsonify({'message': 'some files not deleted', })
        print('some files not deleted')
        resp.status_code = 200
    else:
        resp = jsonify({'message': 'all files deleted'})
        resp.status_code = 200
        print('all files deleted')

    return resp


@app.route("/download_images", methods=['GET', 'POST'])
def download_images():

    print("download")
    if 'files' not in request.args:
        return {'message': 'No files json in request'}

    print(request.args['files'])
    files = json.loads(request.args['files'])['files']

    print('files: ' + str(files))

    # create temp folder
    temp_folder_name = str(uuid.uuid4())
    temp_folder_path = os.path.join(session['dst_folder']['absolute_path'], temp_folder_name)
    if not os.path.exists(temp_folder_path):
        os.mkdir(temp_folder_path)

    # create all image files with bezels

    for file in files:
        src_file_path = os.path.join(session['src_folder']['absolute_path'], file['src_file'])
        dst_file_path = os.path.join(temp_folder_path, file['src_file'])
        shutil.copyfile(src_file_path, dst_file_path)

        file_to_send = bezelify.add_bezel(fp=dst_file_path, bezel_id=file["bezel_id"], stretch=file["stretch"], crop=file["crop"])

        shutil.copyfile(file_to_send, dst_file_path)
        os.remove(file_to_send)

    # create zip file
    def zipdir(path, ziph):
        # ziph is zipfile handle
        for root, dirs, fs in os.walk(path):
            for f in fs:
                print('adding file to ZIP: ' + str(f))
                ziph.write(filename=os.path.join(root, f), arcname=os.path.join(temp_folder_name, f))

    zipfile_path = os.path.join(session['dst_folder']['absolute_path'], 'images.zip')
    zipf = zipfile.ZipFile(zipfile_path, 'w', zipfile.ZIP_DEFLATED)
    zipdir(temp_folder_path, zipf)
    zipf.close()
    mt = mimetypes.types_map[os.path.splitext(zipfile_path)[1]]
    print(mt)

    # send zip file and delete afterwards
    def generate():
        with open(zipfile_path, 'rb') as f:
            yield from f
        shutil.rmtree(temp_folder_path)

    response = app.response_class(generate(), mimetype=mt)
    response.headers.set('Content-Type', 'application/octet-stream; charset=utf-8')
    response.headers.set('Content-Disposition', 'attachment', filename='images.zip')
    return response
