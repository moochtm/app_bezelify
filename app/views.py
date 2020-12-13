from app import app
from app.utils import bezelify

from flask import render_template, request, redirect, send_file
from werkzeug.utils import secure_filename
import os
import uuid
import mimetypes
import shutil

app.config["UPLOADS"] = os.path.dirname(os.path.abspath(__file__)) + '/wip_storage/'
app.config["ALLOWED_IMAGE_EXTENSIONS"] = ["JPEG", "JPG", "PNG", "GIF", "ZIP"]
app.config["MAX_IMAGE_FILESIZE"] = 0.5 * 1024 * 1024


def allowed_image(filename):

    if not "." in filename:
        return False

    ext = filename.rsplit(".", 1)[1]

    if ext.upper() in app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        return True
    else:
        return False


def allowed_image_filesize(filesize):

    if int(filesize) <= app.config["MAX_IMAGE_FILESIZE"]:
        return True
    else:
        return False


@app.route("/", methods=["GET", "POST"])
def upload_image():

    if request.method == "POST":
        if request.files:
            # HANDLE EXCEPTIONS
            if "filesize" in request.cookies:
                if not allowed_image_filesize(request.cookies["filesize"]):
                    print("Filesize exceeded maximum limit")
                    return redirect(request.url)
            file = request.files["file"]

            if file.filename == "":
                print("No filename")
                return redirect(request.url)

            if not allowed_image(file.filename):
                print("That file extension is not allowed")
                return redirect(request.url)

            # PROCESS FILE
            # SAVE FILE
            filename = secure_filename(file.filename)
            temp_working_folder = os.path.join(app.config["UPLOADS"], str(uuid.uuid1()))
            if not os.path.exists(temp_working_folder):
                os.mkdir(temp_working_folder)
            fp = os.path.join(temp_working_folder, filename)
            file.save(fp)
            print("File saved")

            # GET LIST OF INPUT IMAGE FILES
            list_of_input_files = bezelify.unzip_file(fp, temp_working_folder)
            if list_of_input_files is None:
                list_of_input_files = [fp]
            if list_of_input_files is None:
                return 400

            # PROCESS EACH INPUT IMAGE FILE
            files_to_send = []
            for fp in list_of_input_files:
                files_to_send.extend(bezelify.add_bezels(fp, temp_working_folder))

            # GET FILE/S TO SEND BACK
            if len(files_to_send) == 1:
                file_to_send = files_to_send[0]
            elif len(files_to_send) > 1:
                file_to_send = bezelify.create_zip_file(files_to_send, temp_working_folder)
            else:
                return 400

            folder, filename = os.path.split(file_to_send)
            # Get mimetype for file to send
            mt = mimetypes.types_map[os.path.splitext(filename)[1]]

            def generate():
                with open(file_to_send, 'rb') as f:
                    yield from f
                os.remove(file_to_send)
                shutil.rmtree(temp_working_folder)

            r = app.response_class(generate(), mimetype=mt)
            r.headers.set('Content-Disposition', 'attachment', filename=filename)
            return r

    return render_template("public/index.html")


@app.route("/delete_bezel_metadata", methods=["GET"])
def delete_bezel_metadata():
    bezelify.delete_bezel_metadata()
    return "bezel metadata deleted and rebuilt", 200

