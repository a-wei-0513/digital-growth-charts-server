from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory, make_response, jsonify, session
from werkzeug.utils import secure_filename
import markdown
from os import path, listdir, remove
from datetime import datetime
from pathlib import Path

from measurement_request import MeasurementForm
import json

import controllers as controllers

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'UK_WHO' #not very secret - this will need complicating and adding to config

from app import app

# @app.route('/favicon.ico')
# def favicon():
#     return send_from_directory(os.path.join(app.root_path, 'static'),
#                                'favicon.ico', mimetype='image/vnd.microsoft.icon')    

@app.route("/", methods=['GET', 'POST'])
def home():
    form = MeasurementForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            results = controllers.perform_calculations(form)
            # return render_template('test_results.html', results=results)
            session['results'] = results
            return redirect(url_for('results', id='table'))
        # form not validated. Need flash warning here
        return render_template('measurement_form.html', form = form)
    else:
        return render_template('measurement_form.html', form = form)

@app.route("/results/<id>", methods=['GET', 'POST'])
def results(id):
    results = session.get('results')
    if id == 'table':
        return render_template('test_results.html', result = results)
    if id == 'chart':
        return render_template('chart.html')

@app.route("/chart", methods=['GET'])
def chart():
    return render_template('chart.html')

@app.route("/chart_data", methods=['GET'])
def chart_data():
    patient_results = session.get('results')
    data = controllers.plot_centile(patient_results)
    return jsonify({'data': data})

@app.route("/instructions", methods=['GET'])
def instructions():
    #open README.md file
    this_directory = path.abspath(path.dirname(__file__))
    file = path.join(this_directory, 'README.md')
    with open(file) as markdown_file:

        #read contents of file
        content = markdown_file.read()

        #convert to HTML
        html = markdown.markdown(content)
    return render_template('instructions.html', fill=html)

@app.route("/import", methods=['GET', 'POST'])
def import_growth_data():
    if request.method == 'POST':
        ## can only receive .xls, .xlsx, or .csv files
        ## thanks to Chris Griffith, Code Calamity for this code - upload files, chunk if large
        file = request.files['file']
        static_directory = path.join(path.abspath(path.dirname(__file__)), "static/uploaded_data")
        file_to_save = path.join(static_directory, secure_filename(file.filename))
        current_chunk = int(request.form['dzchunkindex'])

        # If the file already exists it's ok if we are appending to it,
        # but not if it's new file that would overwrite the existing one
        if path.exists(file_to_save) and current_chunk == 0:
            # 400 and 500s will tell dropzone that an error occurred and show an error
            return make_response(('File already exists', 400))

        try:
            with open(file_to_save, 'ab') as f:
                f.seek(int(request.form['dzchunkbyteoffset']))
                f.write(file.stream.read())
        except OSError:
            # log.exception will include the traceback so we can see what's wrong 
            print('Could not write to file')
            return make_response(("Not sure why,"
                                " but we couldn't write the file to disk", 500))

        total_chunks = int(request.form['dztotalchunkcount'])

        if current_chunk + 1 == total_chunks:
            # This was the last chunk, the file should be complete and the size we expect
            if path.getsize(file_to_save) != int(request.form['dztotalfilesize']):
                assert(f"File {file.filename} was completed, "
                        f"but has a size mismatch."
                        f"Was {os.path.getsize(save_path)} but we"
                        f" expected {request.form['dztotalfilesize']} ")
                return make_response(('Size mismatch', 500))
            else:
                print(f'File {file.filename} has been uploaded successfully')
                # return make_response('Upload Successful', 200)
                return make_response('success', 200)
        else:
            print(f'Chunk {current_chunk + 1} of {total_chunks} '
                    f'for file {file.filename} complete')

        return make_response("Chunk upload successful", 200)
            
    else:
        return render_template('import.html')

@app.route("/uploaded_data/<id>", methods=['GET', 'POST'])
def uploaded_data(id):
    global requested_data
    if request.method == 'GET':
        static_directory = path.join(path.abspath(path.dirname(__file__)), "static/uploaded_data/")
        if id == 'example':
            file_path = path.join(static_directory, 'dummy_data.xlsx')
            loaded_data = controllers.import_excel_sheet(file_path, False)
            data = json.loads(loaded_data['data'])
            for i in data:
                if(i['birth_date']):
                    i['birth_date'] =  datetime.strftime(datetime.fromtimestamp(i['birth_date']/1000), '%d/%m/%Y')
                if(i['observation_date']):    
                    i['observation_date'] =  datetime.strftime(datetime.fromtimestamp(i['observation_date']/1000), '%d/%m/%Y')
                if(i['estimated_date_delivery']): 
                    i['estimated_date_delivery'] =  datetime.strftime(datetime.fromtimestamp(i['estimated_date_delivery']/1000), '%d/%m/%Y')
            requested_data = data
            return render_template('uploaded_data.html', data=data, unique=loaded_data['unique'])
        if id == 'excel_sheet':
            for file_name in listdir(static_directory):
                if file_name != 'dummy_data.xlsx':
                    file_path = path.join(static_directory, file_name)
                    try:
                        child_data = controllers.import_excel_sheet(file_path, True)
                        data_frame = child_data['data']
                    except ValueError as e: 
                        print(e)
                        flash(f"{e}")
                        data=None
                        render_template('uploaded_data.html', data=data)
                    except LookupError as l:
                        data=None
                        print(l)
                        flash(f"{l}")
                        data=None
                        render_template('uploaded_data.html', data=data)
                    else:
                        data = json.loads(data_frame)
                        for i in data:
                            if(i['birth_date']):
                                i['birth_date'] =  datetime.strftime(datetime.fromtimestamp(i['birth_date']/1000), '%d/%m/%Y')
                            if(i['observation_date']):    
                                i['observation_date'] =  datetime.strftime(datetime.fromtimestamp(i['observation_date']/1000), '%d/%m/%Y')
                            if(i['estimated_date_delivery']): 
                                i['estimated_date_delivery'] =  datetime.strftime(datetime.fromtimestamp(i['estimated_date_delivery']/1000), '%d/%m/%Y')
                        requested_data = data
            return render_template('uploaded_data.html', data=data, unique=child_data['unique'])
        if id=='get_excel':
            excel_file = controllers.download_excel(requested_data)
            temp_directory = Path.cwd().joinpath("static").joinpath('uploaded_data').joinpath('temp')
            return send_from_directory(temp_directory, filename='output.xlsx', as_attachment=True)

@app.route("/references", methods=['GET'])
def references():
    # starting with a hard-coded list, but as it grows probably belongs in database
    with open('./resource_data/growth_reference_repository.json') as json_file:
            data = json.load(json_file)
            json_file.close()
    return render_template('references.html', data=data)

if __name__ == '__main__':
    app.run()
